# Frontend Testing Guide — DB Q&A Integration

**Date:** May 26, 2026  
**Status:** Backend Ready ✅ | Feature Enabled ✅ | Frontend Integration Guide  

---

## 🧪 Step 1: Test Backend API First

Before testing the frontend, verify the backend is working:

### Start Backend

```bash
cd d:\Chat-SystemWorking\IntegratedChatBot
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

**Expected log output:**
```
[WARMUP] Application Database XML store loaded
[STARTUP] Uvicorn running on http://0.0.0.0:8000
```

### Test with cURL

```bash
# Test 1: List all active users
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "show all active users",
    "session_id": "test_1",
    "beautify": true,
    "user_id": "U001",
    "role_id": "101"
  }' | jq .

# Expected Response:
# {
#   "response_text": "...(beautified response)...",
#   "result_type": "db_query_beautified",
#   "db_intent": "USER_LIST_ACTIVE",
#   "db_found": true,
#   "db_records": [...],
#   "db_summary": "Found 5 active users",
#   "db_beautified": "..."
# }
```

### Test with Python (Postman Alternative)

```python
import requests
import json

response = requests.post(
    "http://localhost:8000/chat",
    json={
        "message": "list all departments",
        "session_id": "test_2",
        "beautify": True,
        "user_id": "U001",
        "role_id": "101"
    }
)

result = response.json()
print(json.dumps(result, indent=2))

# Check the response structure
print(f"Intent: {result.get('db_intent')}")
print(f"Found: {result.get('db_found')}")
print(f"Records: {len(result.get('db_records', []))} items")
print(f"Beautified: {result.get('db_beautified')[:100]}...")
```

---

## 🎨 Step 2: Update Frontend to Display DB Q&A Results

### Current Frontend Structure

```
frontend/
├── src/
│   ├── App.jsx                  ← Main app component
│   ├── components/
│   │   ├── ChatWindow.jsx       ← Messages display
│   │   ├── MessageBubble.jsx    ← Individual message
│   │   └── VoiceInput.jsx
│   └── services/
│       └── api.js               ← API calls
```

### Update `frontend/src/services/api.js`

Add support for the new DB Q&A response fields:

```javascript
// frontend/src/services/api.js

const API_BASE_URL = "http://localhost:8000";

export async function sendMessage(message, sessionId, options = {}) {
  const {
    beautify = true,
    userId = "U001",
    roleId = "101",
    conversationHistory = []
  } = options;

  const response = await fetch(`${API_BASE_URL}/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      message: message,
      session_id: sessionId,
      beautify: beautify,
      user_id: userId,
      role_id: roleId,
      conversation_history: conversationHistory,
    }),
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }

  return await response.json();
}

// Helper to check if response is from DB Q&A
export function isDbQaResponse(data) {
  return (
    data.result_type === "db_query_beautified" ||
    data.result_type === "db_query" ||
    data.db_intent !== undefined
  );
}

// Helper to format DB Q&A response for display
export function formatDbQaResponse(data) {
  return {
    text: data.db_beautified || data.response_text,
    intent: data.db_intent,
    found: data.db_found,
    records: data.db_records || [],
    summary: data.db_summary,
    isDbQuery: true,
  };
}
```

### Update `frontend/src/components/MessageBubble.jsx`

Enhance the message bubble to handle DB Q&A responses with tables:

```javascript
// frontend/src/components/MessageBubble.jsx

import React from "react";
import "../App.css";

export default function MessageBubble({ message, isUserMessage }) {
  const renderDbQaResponse = (message) => {
    if (!message.isDbQuery) {
      return message.text;
    }

    return (
      <div className="db-qa-response">
        {/* Main Response Text */}
        <p className="response-text">{message.text}</p>

        {/* Summary Badge */}
        {message.summary && (
          <div className="summary-badge">
            📊 {message.summary}
          </div>
        )}

        {/* Data Table (if records available) */}
        {message.records && message.records.length > 0 && (
          <div className="records-table">
            <table>
              <thead>
                <tr>
                  {Object.keys(message.records[0]).map((key) => (
                    <th key={key}>{key}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {message.records.map((record, idx) => (
                  <tr key={idx}>
                    {Object.values(record).map((value, i) => (
                      <td key={i}>{String(value).substring(0, 50)}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Intent Badge */}
        {message.intent && (
          <div className="intent-badge">
            Intent: <code>{message.intent}</code>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className={`message ${isUserMessage ? "user" : "bot"}`}>
      <div className="message-content">
        {typeof message === "string" ? message : renderDbQaResponse(message)}
      </div>
    </div>
  );
}
```

### Update `frontend/src/App.jsx`

Integrate the new API helpers:

```javascript
// frontend/src/App.jsx

import React, { useState, useRef, useEffect } from "react";
import ChatWindow from "./components/ChatWindow";
import MessageBubble from "./components/MessageBubble";
import VoiceInput from "./components/VoiceInput";
import { sendMessage, isDbQaResponse, formatDbQaResponse } from "./services/api";
import "./App.css";

function App() {
  const [messages, setMessages] = useState([]);
  const [sessionId, setSessionId] = useState(
    `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
  );
  const [userId, setUserId] = useState("U001");
  const [roleId, setRoleId] = useState("101");
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSendMessage = async (userMessage) => {
    if (!userMessage.trim()) return;

    // Add user message to chat
    const userMsg = { text: userMessage, isUser: true };
    setMessages((prev) => [...prev, userMsg]);
    setIsLoading(true);

    try {
      // Send to backend API
      const response = await sendMessage(userMessage, sessionId, {
        userId,
        roleId,
        beautify: true,
        conversationHistory: messages,
      });

      // Check if response is DB Q&A
      let botMessage;
      if (isDbQaResponse(response)) {
        // Format DB Q&A response
        botMessage = formatDbQaResponse(response);
      } else {
        // Regular response
        botMessage = { text: response.response_text, isUser: false };
      }

      setMessages((prev) => [...prev, botMessage]);
    } catch (error) {
      console.error("Error:", error);
      const errorMsg = {
        text: `Error: ${error.message}`,
        isUser: false,
        isError: true,
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="App">
      <div className="header">
        <h1>💬 Report Assistant with DB Q&A</h1>
        <div className="user-info">
          <input
            type="text"
            placeholder="User ID"
            value={userId}
            onChange={(e) => setUserId(e.target.value)}
          />
          <input
            type="text"
            placeholder="Role ID"
            value={roleId}
            onChange={(e) => setRoleId(e.target.value)}
          />
        </div>
      </div>

      <ChatWindow messages={messages} onSendMessage={handleSendMessage} />

      <div ref={messagesEndRef} />

      {isLoading && <div className="loading">⏳ Processing...</div>}
    </div>
  );
}

export default App;
```

### Update `frontend/src/App.css`

Add styles for DB Q&A responses:

```css
/* frontend/src/App.css */

/* DB Q&A Response Styling */
.db-qa-response {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 1rem;
  border-radius: 8px;
  color: white;
  margin: 0.5rem 0;
}

.response-text {
  font-size: 1rem;
  line-height: 1.5;
  margin: 0 0 1rem 0;
}

.summary-badge {
  background: rgba(255, 255, 255, 0.2);
  padding: 0.5rem 1rem;
  border-radius: 20px;
  font-size: 0.9rem;
  margin: 0.5rem 0;
  display: inline-block;
}

.intent-badge {
  background: rgba(0, 0, 0, 0.2);
  padding: 0.5rem 1rem;
  border-radius: 4px;
  font-size: 0.85rem;
  margin-top: 0.5rem;
  font-family: monospace;
}

.records-table {
  margin: 1rem 0;
  overflow-x: auto;
  background: rgba(0, 0, 0, 0.1);
  border-radius: 4px;
  padding: 0.5rem;
}

.records-table table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.9rem;
}

.records-table th {
  background: rgba(0, 0, 0, 0.2);
  padding: 0.5rem;
  text-align: left;
  font-weight: bold;
  border-bottom: 2px solid rgba(255, 255, 255, 0.3);
}

.records-table td {
  padding: 0.5rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  word-break: break-word;
}

.records-table tr:hover {
  background: rgba(0, 0, 0, 0.1);
}

/* User info input styling */
.user-info {
  display: flex;
  gap: 1rem;
  margin-top: 1rem;
}

.user-info input {
  padding: 0.5rem;
  border: 1px solid #ccc;
  border-radius: 4px;
  font-size: 0.9rem;
}

.loading {
  text-align: center;
  padding: 1rem;
  color: #666;
  font-style: italic;
}
```

---

## 🎯 Step 3: Test Frontend with Sample Queries

### Start Everything

**Terminal 1: Backend**
```bash
cd IntegratedChatBot
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2: Frontend**
```bash
cd IntegratedChatBot/frontend
npm install
npm run dev
```

**Terminal 3: Open Browser**
```
http://localhost:3000
```

### Sample Test Queries

#### Test 1: DB Q&A Query (Intent Matched)
```
User: "show all active users"

Expected Response:
- Result Type: db_query_beautified
- Intent: USER_LIST_ACTIVE
- Display: Beautified text + table of active users
- Table columns: id, name, department, active_status
```

#### Test 2: DB Q&A Query (Different Intent)
```
User: "list all departments"

Expected Response:
- Result Type: db_query_beautified
- Intent: DEPT_LIST
- Display: Formatted list of departments with counts
```

#### Test 3: Regular Query (Falls Through to LLM)
```
User: "what is the meaning of life"

Expected Response:
- Result Type: unknown (or standard response)
- Display: Regular LLM response (no DB Q&A fields)
```

#### Test 4: Access Control (Non-Admin)
```
Change Role ID to: 999
User: "show all users"

Expected Response:
- Intent: USER_LIST
- db_found: false
- Message: "Access denied" or similar
```

#### Test 5: Report Query (Existing Feature)
```
User: "show status of R091"

Expected Response:
- Falls through to standard report lookup
- Regular response format (not DB Q&A)
```

---

## 🔍 Step 4: Console Debugging

Open Browser DevTools (F12) and check Console for response structure:

```javascript
// In browser console, paste this after sending a message
// This will log the last API response

// Or add this to App.jsx for debugging:
useEffect(() => {
  console.log("All messages:", messages);
}, [messages]);

// Look for:
// ✅ db_intent field present
// ✅ db_found = true/false
// ✅ db_records array populated
// ✅ db_beautified text present
```

---

## ✅ Testing Checklist

### Backend Tests (All Should Pass)
- [ ] Backend starts without errors
- [ ] "[WARMUP] Application Database XML store loaded" appears in logs
- [ ] cURL request returns `db_*` fields
- [ ] Response contains `result_type: "db_query_beautified"`

### Frontend Tests
- [ ] Frontend starts at http://localhost:3000
- [ ] User can type messages
- [ ] DB Q&A queries display beautified responses
- [ ] Records table renders correctly
- [ ] Intent badge shows intent name
- [ ] Summary badge shows count/summary

### Feature Tests
- [ ] Query: "show all users" → USER_LIST intent
- [ ] Query: "list active users" → USER_LIST_ACTIVE intent
- [ ] Query: "what are departments" → DEPT_LIST intent
- [ ] Change role ID to 999 and retry → Access denied
- [ ] Regular query "how to write reports" → Falls to LLM (no DB fields)

### Visual Tests
- [ ] Message bubbles display correctly
- [ ] DB Q&A responses have purple gradient background
- [ ] Tables are readable
- [ ] Intent and summary badges render
- [ ] No console errors

---

## 🚨 Troubleshooting

### Backend Starts But No XML Store Log

**Problem:** `[WARMUP] Application Database XML store loaded` doesn't appear

**Check:**
```bash
# Verify APP_DB_BASE_PATH is set in .env
cat .env | grep APP_DB_BASE_PATH

# Should show:
# APP_DB_BASE_PATH=D:\Repo\Repo5.5 3\Repo5.5\Database
```

**Fix:**
- If empty: Set it to actual Database directory
- If path invalid: Check directory exists and contains XML files

### Frontend Can't Connect to Backend

**Problem:** CORS error or "Cannot reach server"

**Check:**
```bash
# Verify CORS_ORIGINS includes frontend origin
cat .env | grep CORS_ORIGINS
# Should include: http://localhost:3000
```

**Fix:**
```bash
# If missing, add to .env:
CORS_ORIGINS=http://localhost:3000
```

### Intent Not Matching

**Problem:** Query returns `db_intent: null`

**Possible Causes:**
1. Feature disabled (`APP_DB_BASE_PATH` empty)
2. Query doesn't match any pattern
3. Query matches but classified as UNKNOWN

**Debug:**
```python
# Test intent classification directly
from backend.db_qa.intent_classifier import classify

intent, params = classify("show all users")
print(f"Intent: {intent}, Params: {params}")

# Should return: USER_LIST intent
```

### Table Not Rendering

**Problem:** Records array empty or not displaying

**Check Browser DevTools:**
```javascript
console.log("Last message:", messages[messages.length - 1]);
// Check if db_records array is populated
```

**Fix:**
- Verify `db_records` is in response
- Check table CSS is loaded
- Ensure records have data

---

## 📊 Response Structure Reference

### DB Q&A Response (for Frontend)

```javascript
{
  "response_text": "...",           // Main formatted response
  "result_type": "db_query_beautified",  // Indicates DB Q&A
  "db_intent": "USER_LIST",         // Intent name
  "db_found": true,                 // Did query succeed
  "db_records": [                   // Structured data rows
    {
      "id": "U001",
      "name": "Admin User",
      "department": "IT",
      "active": true
    },
    // ... more rows
  ],
  "db_summary": "Found 5 active users",  // Quick summary
  "db_beautified": "..."            // Full LLM-formatted response
}
```

### How to Detect & Display

```javascript
// frontend/src/services/api.js
export function isDbQaResponse(data) {
  return data.db_intent !== undefined;
}

// frontend/src/components/MessageBubble.jsx
if (message.isDbQuery) {
  // Show table + summary + intent badge
} else {
  // Show plain text
}
```

---

## 🎬 Quick Start Video Script

1. **Start Backend**
   ```bash
   cd IntegratedChatBot
   uvicorn backend.main:app --reload
   ```

2. **Start Frontend**
   ```bash
   cd IntegratedChatBot/frontend
   npm run dev
   ```

3. **Open Browser**
   - Go to http://localhost:3000

4. **Test Query #1** (DB Q&A)
   - Type: "show all active users"
   - See: Beautified response + table

5. **Test Query #2** (Regular)
   - Type: "how do I submit a return?"
   - See: Regular LLM response

6. **Test Query #3** (Access Control)
   - Change Role ID to "999"
   - Type: "show all users"
   - See: Access denied message

---

## 📚 Next Steps

1. ✅ Test backend API with cURL
2. ✅ Copy API helper code to frontend
3. ✅ Update MessageBubble to display DB Q&A responses
4. ✅ Add styling for tables and badges
5. ✅ Test with various queries
6. ✅ Verify access control works
7. ✅ Check console for any errors

**Status:** Ready for frontend testing! 🚀

