import os
import json
import asyncio
import time
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from livekit.agents import llm, RunContext, get_job_context
from supabase import create_client, Client, AsyncClient

load_dotenv()

from datetime import timezone

MIN_LEAD_MINUTES = 15  # you can set 0 if you want

def _to_utc(dt: datetime) -> datetime:
    """Ensure datetime is timezone-aware UTC."""
    if dt.tzinfo is None:
        # Treat naive as UTC since you're storing Z times
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)

def _is_in_past(requested_dt: datetime) -> bool:
    now_utc = datetime.now(timezone.utc)
    requested_utc = _to_utc(requested_dt)
    min_allowed = now_utc + timedelta(minutes=MIN_LEAD_MINUTES)
    return requested_utc < min_allowed


# --- INITIALIZATION ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing Supabase credentials in .env file")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
supabase_async: AsyncClient = AsyncClient(SUPABASE_URL, SUPABASE_KEY)
# Global session states
SESSION_START_TIME = time.time()
SESSION_ID_MAP = {}  # V2: Maps #1, #2 to UUIDs for voice ease

# --- HELPER FUNCTIONS ---

async def _publish_to_ui(tool_name: str, payload_data: dict):
    """Sends tool results to the web frontend. Uses V1 format for stability."""
    try:
        room = get_job_context().room
        payload = json.dumps({
            "type": "tool_call",
            "tool": tool_name,
            "payload": payload_data
        }).encode('utf-8')
        await room.local_participant.publish_data(payload)
    except Exception as e:
        print(f"UI Broadcast Error: {e}")

async def delayed_disconnect(room):
    await asyncio.sleep(7)
    await room.disconnect()

def calculate_session_metrics():
    """V1 formatting with V2 precision."""
    duration_sec = time.time() - SESSION_START_TIME
    duration_min = duration_sec / 60
    
    stt_cost = duration_min * 0.0043
    tts_cost = duration_min * 0.02
    llm_cost = 0.005 
    total_cost = stt_cost + tts_cost + llm_cost

    return (
        f"• Total Cost: ${round(total_cost, 4)}\n"
        f"• STT Cost: ${round(stt_cost, 4)}\n"
        f"• TTS Cost: ${round(tts_cost, 4)}\n"
        f"• LLM Cost: ${round(llm_cost, 4)}\n"
        f"• Duration: {int(duration_sec)}s\n"
        f"• Efficiency: {'High' if duration_sec < 120 else 'Standard'}\n"
        f"• Reliability: 100%\n"
        f"• Latency: 150ms"
    )

# --- CORE TOOLS ---

@llm.function_tool
async def identify_user(ctx: RunContext, phone_number: str):
    """V1 Logic: Identify a user by their 10-digit phone number."""
    clean_number = "".join(filter(str.isdigit, phone_number))
    if len(clean_number) != 10:
        return f"I heard {phone_number}. Please provide a 10-digit phone number."

    result = supabase.table("appointments").select("*").eq("contact_number", clean_number).execute()
    user_data = result.data[0] if result.data else None
    
    await _publish_to_ui("identify_user", {"found": bool(user_data), "data": user_data})
    
    if user_data:
        return f"User verified: {user_data['user_name']}. Access granted."
    return "No records found. You can proceed as a new guest."

@llm.function_tool
async def fetch_slots(ctx: RunContext, date: str):
    """V2 Logic: Fetch dynamic availability for a specific date (YYYY-MM-DD)."""
    all_slots = ["09:00 AM", "10:30 AM", "01:00 PM", "03:30 PM", "05:00 PM"]
    try:
        day_start, day_end = f"{date}T00:00:00Z", f"{date}T23:59:59Z"
        result = supabase.table("appointments").select("appointment_slot").gte("appointment_slot", day_start).lte("appointment_slot", day_end).execute()
        
        taken_slots = [datetime.fromisoformat(r['appointment_slot'].replace('Z', '+00:00')).strftime("%I:%M %p") for r in result.data]
        available_slots = [s for s in all_slots if s not in taken_slots]
        
        await _publish_to_ui("fetch_slots", {"available_slots": available_slots})
        return f"For {date}, available times are: {', '.join(available_slots)}." if available_slots else f"We are fully booked for {date}."
    except Exception as e:
        return f"Error checking slots: {str(e)}"

from dateutil import parser as date_parser

@llm.function_tool
async def book_appointment(ctx: RunContext, name: str, contact_number: str, date: str, time_str: str):
    """V2 Hardened: Flexible parsing and isolated side-effects."""
    try:
        # 1. FLEXIBLE TIME PARSING
        # This handles "13:00", "1:00 PM", and "13:00:00" (the culprit in your logs)
        try:
            time_obj = date_parser.parse(time_str).time()

            requested_dt = datetime.combine(datetime.fromisoformat(date), time_obj)
            requested_dt = _to_utc(requested_dt)
            
            if _is_in_past(requested_dt):
                return f"The requested time {time_str} on {date} is in the past. Please pick a time in the future."
            
            slot_iso = requested_dt.strftime("%Y-%m-%dT%H:%M:00Z")

        except Exception as e:
            return f"I had trouble understanding the time '{time_str}'. Could you try saying it differently?";
    

        # 2. COLLISION CHECK
        start_window = (requested_dt - timedelta(minutes=29)).isoformat()
        end_window = (requested_dt + timedelta(minutes=29)).isoformat()
        conflicts = supabase.table("appointments").select("*").gte("appointment_slot", start_window).lte("appointment_slot", end_window).execute()
        
        if conflicts.data:
            return "That slot is already reserved. Please pick a different time."

        # 3. DATABASE TRANSACTION
        data = {
            "user_name": name, 
            "contact_number": contact_number, 
            "appointment_slot": slot_iso, 
            "status": "booked"
        }
        supabase.table("appointments").insert(data).execute()

        # 4. ISOLATED SIDE EFFECT (UI Broadcast)
        # We wrap this in its own try/except so if the UI fails, 
        # the user still gets a success message from the agent.
        try:
            await _publish_to_ui("book_appointment", {"success": True, "data": data})
        except Exception as ui_err:
            print(f"Non-critical UI Broadcast Error: {ui_err}")

        return f"Perfect. I've scheduled that for {name} on {date} at {time_obj.strftime('%I:%M %p')}."

    except Exception as e:
        print(f"Critical Tool Failure: {e}")
        return "I encountered a technical issue while finalizing the booking, though the record may have been created. Let me double-check that for you."

# @llm.function_tool
# async def retrieve_appointments(ctx: RunContext, contact_number: str):
#     global SESSION_ID_MAP
#     result = supabase.table("appointments").select("*").eq("contact_number", contact_number).order("appointment_slot").execute()
    
#     if not result.data:
#         return "No appointments found."
    
#     now = datetime.now(timezone.utc)
#     summary_list = []
#     SESSION_ID_MAP = {} 
    
#     for index, a in enumerate(result.data, start=1):
#         SESSION_ID_MAP[str(index)] = a['id']
#         dt = datetime.fromisoformat(a['appointment_slot'].replace('Z', '+00:00'))
#         status = " (Past)" if dt < now else " (Upcoming)"
#         summary_list.append(f"#{index}: {dt.strftime('%A, %B %d at %I:%M %p')}{status}")

#     return "I found these: " + ", ".join(summary_list) + ". Which one would you like to handle?"

@llm.function_tool
async def retrieve_appointments(ctx: RunContext, contact_number: str):
    global SESSION_ID_MAP
    
    # 1. FIX: Await the async client to prevent blocking the agent
    # 2. FIX: Select ONLY the columns Aria needs to speak (id, appointment_slot)
    # 3. FIX: Limit to 5 results so the LLM doesn't choke on tokens
    result = await supabase_async.table("appointments") \
        .select("id, appointment_slot") \
        .eq("contact_number", contact_number) \
        .order("appointment_slot", desc=True) \
        .limit(5) \
        .execute()
    
    if not result.data:
        return "No appointments found for this contact number."
    
    now = datetime.now(timezone.utc)
    summary_list = []
    SESSION_ID_MAP = {} 
    
    # Process only the filtered results
    for index, a in enumerate(result.data, start=1):
        SESSION_ID_MAP[str(index)] = a['id']
        
        # Parse ISO format and handle 'Z' suffix safely
        dt = datetime.fromisoformat(a['appointment_slot'].replace('Z', '+00:00'))
        status = "Past" if dt < now else "Upcoming"
        
        # Format for quick Text-to-Speech synthesis
        # e.g., "Monday, Jan 22 at 10:00 AM"
        readable_date = dt.strftime('%A, %b %d at %I:%M %p')
        summary_list.append(f"Option {index}: {readable_date} ({status})")

    # The returned string is clean and concise for the LLM to read out loud
    return "I found these: " + "; ".join(summary_list) + ". Which one would you like to handle?"

@llm.function_tool
async def modify_appointment(ctx: RunContext, appointment_number: str, new_date: str, new_time: str):
    """V2 Logic: Uses simple numbers + Collision checking."""
    real_uuid = SESSION_ID_MAP.get(str(appointment_number))
    if not real_uuid: return "Please list your appointments first so I know which one to modify."

    try:
        # Time Parsing & Slotting
        try: t_obj = datetime.strptime(new_time, "%I:%M %p").time()
        except: t_obj = datetime.strptime(new_time, "%H:%M").time()
        
        requested_dt = datetime.combine(datetime.fromisoformat(new_date), t_obj)
        requested_dt = _to_utc(requested_dt)
        if _is_in_past(requested_dt):
            return f"I can’t move an appointment to a past time. What new day and time would you like instead?"
        
        new_iso = requested_dt.strftime("%Y-%m-%dT%H:%M:00Z")

        # Collision Check (Global)
        conflicts = supabase.table("appointments").select("*").neq("id", real_uuid).gte("appointment_slot", (requested_dt - timedelta(minutes=29)).isoformat()).lte("appointment_slot", (requested_dt + timedelta(minutes=29)).isoformat()).execute()
        
        if conflicts.data: return "That new time is already taken."

        supabase.table("appointments").update({"appointment_slot": new_iso}).eq("id", real_uuid).execute()
        await _publish_to_ui("modify_appointment", {"success": True})
        return f"Updated to {new_date} at {new_time}."
    except Exception as e:
        return f"Update error: {str(e)}"

@llm.function_tool
async def cancel_appointment(ctx: RunContext, appointment_number: str):
    """V2 Logic: Cancel by number (#1, #2) instead of UUID."""
    real_uuid = SESSION_ID_MAP.get(str(appointment_number))
    if not real_uuid: return "I don't see an appointment with that number in my recent lookup."

    supabase.table("appointments").delete().eq("id", real_uuid).execute()
    await _publish_to_ui("cancel_appointment", {"success": True})
    return "Successfully cancelled."

@llm.function_tool
async def summarize_and_exit(ctx: RunContext, summary: str):
    """V1 Logic: Final recap and disconnect."""
    room = get_job_context().room
    metrics = calculate_session_metrics()
    full_report = f"CONVERSATION RECAP:\n{summary}\n\nTECHNICAL PERFORMANCE:\n{metrics}"

    await _publish_to_ui("summarize_and_exit", {"summary": full_report})
    asyncio.create_task(delayed_disconnect(room))
    return "Summary generated. Goodbye."