# ARIA : AI Voice Concierge 🎙️🤖

**ARIA** is a real-time AI Voice Concierge built on the **LiveKit Agents framework**, combining **natural human-like conversation** with **strict business logic** to handle **appointment booking, identification, and schedule management**.

ARIA is designed as a **multi-tenant, real-time voice AI system** capable of serving multiple users simultaneously with full session isolation.

DEMO-LINK : https://drive.google.com/file/d/1XpF4LmGuXprVpkzkj55ZtNulvMXKm-V0/view?usp=sharing

---

## 🛠️ Architecture & Tech Stack

ARIA follows a **multi-tenant architecture**, enabling scalable and isolated interactions for concurrent users.

---

## 🧠 Intelligence Layer

### OpenAI GPT-4o-mini
The Large Language Model (LLM) acts as the **brain** of ARIA.

**Responsibilities**
- **Natural Language Understanding**: Interprets user intent accurately
- **Logical Orchestration**: Determines which internal tools to invoke (`identify_user`, `book_appointment`, etc.)
- **Conversational Constitution**: Enforces security, identity verification, and professional behavior
- **Context Management**: Tracks the conversation lifecycle from greeting to task completion

---

## 🎙️ Voice Processing

### Deepgram & Cartesia

These plugins enable seamless real-time voice interaction.

- **Deepgram (STT)**  
  High-speed Speech-to-Text for real-time transcription

- **Cartesia (TTS)**  
  Neural Text-to-Speech engine producing natural, expressive responses

---

## 🌐 Real-Time Infrastructure

### LiveKit (WebRTC)

LiveKit powers low-latency communication.

- **WebRTC Transport**: Audio/video streaming
- **Data Channels**: JSON status packets for live UI updates
- **Participant Management**: Handles session lifecycle and stability

---

## ⚙️ Backend

### FastAPI

The FastAPI server acts as the **administrative gateway**.

- **Token Orchestration**: Generates LiveKit access tokens
- **Dynamic Room Allocation**: Unique rooms per session
- **Session Isolation**: Multiple users interact with their own AI instance simultaneously

---

## 🗄️ Database

### Supabase (PostgreSQL)

Used for all persistent data storage.

- **Appointments Management**
- **Atomic Transactions** (booking, modification, cancellation)
- **Collision Prevention**
- **Real-time Availability Queries**

---

## 🎨 Frontend

### HTML5 + Tailwind CSS

Delivers a premium, modern UI.

- **Glassmorphism Design**
- **Dark Mode Aesthetic**
- **LiveKit Client SDK**
- **Real-Time Session Summary Panel**
- **Microphone Controls (mute/unmute/end session)**

---

## ✨ Core Features

### 🛡️ Conversational Constitution
ARIA operates under strict, non-negotiable rules:

- **Identity Pinning**  
  Access only after 10-digit phone number verification

- **Verification Engine**  
  Mandatory read-back of:
  - Name
  - Date
  - Time

- **Multi-Appointment Ambiguity Protocol**  
  Uses reference numbers (`#1`, `#2`, etc.) to prevent accidental actions

---

### 🕒 Temporal Intelligence
- Timezone-aware
- Resolves relative phrases like *“tomorrow”* or *“next week”*
- Anchors all dates before querying availability

---

### 💎 Dynamic Visual Sync
- Publishes real-time status packets to frontend
- Friendly UI messages such as:
  - *“Verifying identity…”*
  - *“Finding available slots…”*
- Masks backend latency gracefully

---

## 📂 Project Structure

### 1️⃣ `agent.py` — **The Brain**
- Defines AI persona and system prompt
- Implements Naturalism Protocol:
  - Backchanneling (“mm-hm”)
  - Latency fillers
- Handles conversational flow and events

---

### 2️⃣ `tools.py` — **The Muscle**
Database interaction layer using Supabase.

**Available Tools**
- `identify_user`
- `fetch_slots`
- `book_appointment`
- `retrieve_appointment`
- `cancel_appointments`
- `modify_appointments`
- `end_conversation`
- `summarize_and_exit`  
  (Generates technical performance report with STT/TTS/LLM cost estimates)

---

### 3️⃣ `server.py` — **The Gatekeeper**
- FastAPI server
- Generates LiveKit access tokens
- Manages multi-tenant session isolation

---

### 4️⃣ `index.html` — **The Face**
High-end user interface featuring:

- Neural intelligence animations
- Live session summary panel
- Real-time microphone control
- Voice & avatar playback

---

## 🔐 Environment Variables

Create a `.env` file with the following:

```env
LIVEKIT_API_KEY=your_key
LIVEKIT_API_SECRET=your_secret
SUPABASE_URL=your_url
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
OPENAI_API_KEY=your_openai_key



