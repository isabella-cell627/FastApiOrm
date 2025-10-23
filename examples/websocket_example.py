import asyncio
from fastapi import FastAPI, WebSocket, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from contextlib import asynccontextmanager

from fastapi_orm import (
    Database,
    Model,
    IntegerField,
    StringField,
    BooleanField,
    DateTimeField,
    ConnectionManager,
    WebSocketSubscriptionManager,
    websocket_lifespan,
    create_websocket_route_handler,
)

db = Database("sqlite+aiosqlite:///./websocket_demo.db")

manager = ConnectionManager(enable_heartbeat=True, heartbeat_interval=30)


class Task(Model):
    __tablename__ = "tasks"

    id: int = IntegerField(primary_key=True)
    title: str = StringField(max_length=200, nullable=False)
    description: str = StringField(max_length=1000, nullable=True)
    completed: bool = BooleanField(default=False)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)


class User(Model):
    __tablename__ = "users"

    id: int = IntegerField(primary_key=True)
    username: str = StringField(max_length=100, nullable=False, unique=True)
    email: str = StringField(max_length=255, nullable=False, unique=True)
    is_active: bool = BooleanField(default=True)
    created_at = DateTimeField(auto_now_add=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    await db.create_tables()
    
    manager.register_model_events(Task, channel="tasks")
    manager.register_model_events(User, channel="users")
    
    print("✅ Database initialized")
    print("✅ WebSocket manager initialized")
    print(f"📡 Real-time events enabled for: Task, User")
    
    yield
    
    await manager.close_all()
    await db.close()
    print("👋 Application shutdown complete")


app = FastAPI(
    title="FastAPI ORM WebSocket Example",
    description="Real-time database updates via WebSocket",
    lifespan=lifespan
)


async def get_db():
    async for session in db.get_session():
        yield session


html_template = """
<!DOCTYPE html>
<html>
<head>
    <title>FastAPI ORM WebSocket Demo</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }
        .container {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        h1 { color: #333; }
        h2 { color: #666; border-bottom: 2px solid #4CAF50; padding-bottom: 10px; }
        .status { 
            padding: 10px;
            border-radius: 4px;
            margin: 10px 0;
            font-weight: bold;
        }
        .connected { background: #4CAF50; color: white; }
        .disconnected { background: #f44336; color: white; }
        #events {
            background: #f9f9f9;
            border: 1px solid #ddd;
            border-radius: 4px;
            padding: 15px;
            height: 400px;
            overflow-y: auto;
            font-family: monospace;
            font-size: 12px;
        }
        .event {
            padding: 8px;
            margin: 4px 0;
            border-radius: 4px;
            border-left: 4px solid #4CAF50;
            background: white;
        }
        .event.create { border-left-color: #4CAF50; }
        .event.update { border-left-color: #2196F3; }
        .event.delete { border-left-color: #f44336; }
        .event.heartbeat { border-left-color: #9E9E9E; opacity: 0.6; }
        button {
            background: #4CAF50;
            color: white;
            padding: 10px 20px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            margin: 5px;
            font-size: 14px;
        }
        button:hover { background: #45a049; }
        button.danger { background: #f44336; }
        button.danger:hover { background: #da190b; }
        input, textarea {
            width: 100%;
            padding: 8px;
            margin: 5px 0;
            border: 1px solid #ddd;
            border-radius: 4px;
            box-sizing: border-box;
        }
        .form-group { margin: 15px 0; }
        label { display: block; margin-bottom: 5px; font-weight: bold; }
        .channel-selector {
            display: flex;
            gap: 10px;
            margin: 15px 0;
        }
    </style>
</head>
<body>
    <h1>🚀 FastAPI ORM WebSocket Demo</h1>
    
    <div class="container">
        <h2>Connection Status</h2>
        <div id="status" class="status disconnected">Disconnected</div>
        
        <div class="channel-selector">
            <button onclick="connectToChannel('tasks')">Connect to Tasks Channel</button>
            <button onclick="connectToChannel('users')">Connect to Users Channel</button>
            <button onclick="disconnectWebSocket()" class="danger">Disconnect</button>
        </div>
    </div>
    
    <div class="container">
        <h2>Create Task</h2>
        <div class="form-group">
            <label>Title:</label>
            <input type="text" id="task-title" placeholder="Enter task title">
        </div>
        <div class="form-group">
            <label>Description:</label>
            <textarea id="task-description" placeholder="Enter task description" rows="3"></textarea>
        </div>
        <button onclick="createTask()">Create Task</button>
        <button onclick="toggleTask()" class="danger">Toggle Last Task</button>
    </div>
    
    <div class="container">
        <h2>Create User</h2>
        <div class="form-group">
            <label>Username:</label>
            <input type="text" id="user-username" placeholder="Enter username">
        </div>
        <div class="form-group">
            <label>Email:</label>
            <input type="text" id="user-email" placeholder="Enter email">
        </div>
        <button onclick="createUser()">Create User</button>
    </div>
    
    <div class="container">
        <h2>Real-time Events</h2>
        <button onclick="clearEvents()">Clear Events</button>
        <div id="events"></div>
    </div>
    
    <script>
        let ws = null;
        let currentChannel = null;
        let lastTaskId = null;
        
        function connectToChannel(channel) {
            if (ws) {
                ws.close();
            }
            
            currentChannel = channel;
            ws = new WebSocket(`ws://localhost:5000/ws/${channel}`);
            
            ws.onopen = function(event) {
                document.getElementById('status').className = 'status connected';
                document.getElementById('status').textContent = `Connected to ${channel} channel`;
                addEvent('connection', { message: `Connected to ${channel}` });
            };
            
            ws.onmessage = function(event) {
                const data = JSON.parse(event.data);
                addEvent(data.type, data);
                
                if (data.type === 'create' && data.model === 'Task') {
                    lastTaskId = data.data.id;
                }
            };
            
            ws.onclose = function(event) {
                document.getElementById('status').className = 'status disconnected';
                document.getElementById('status').textContent = 'Disconnected';
                addEvent('disconnection', { message: 'Disconnected from server' });
            };
            
            ws.onerror = function(error) {
                addEvent('error', { message: 'WebSocket error occurred' });
            };
        }
        
        function disconnectWebSocket() {
            if (ws) {
                ws.close();
                ws = null;
            }
        }
        
        async function createTask() {
            const title = document.getElementById('task-title').value;
            const description = document.getElementById('task-description').value;
            
            if (!title) {
                alert('Please enter a task title');
                return;
            }
            
            const response = await fetch('/tasks', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ title, description })
            });
            
            if (response.ok) {
                document.getElementById('task-title').value = '';
                document.getElementById('task-description').value = '';
            }
        }
        
        async function toggleTask() {
            if (!lastTaskId) {
                alert('Create a task first');
                return;
            }
            
            await fetch(`/tasks/${lastTaskId}/toggle`, { method: 'PUT' });
        }
        
        async function createUser() {
            const username = document.getElementById('user-username').value;
            const email = document.getElementById('user-email').value;
            
            if (!username || !email) {
                alert('Please enter username and email');
                return;
            }
            
            const response = await fetch('/users', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, email })
            });
            
            if (response.ok) {
                document.getElementById('user-username').value = '';
                document.getElementById('user-email').value = '';
            }
        }
        
        function addEvent(type, data) {
            const eventsDiv = document.getElementById('events');
            const eventDiv = document.createElement('div');
            eventDiv.className = `event ${type}`;
            
            const timestamp = new Date().toLocaleTimeString();
            eventDiv.innerHTML = `
                <strong>[${timestamp}] ${type.toUpperCase()}</strong><br>
                ${JSON.stringify(data, null, 2)}
            `;
            
            eventsDiv.insertBefore(eventDiv, eventsDiv.firstChild);
            
            while (eventsDiv.children.length > 50) {
                eventsDiv.removeChild(eventsDiv.lastChild);
            }
        }
        
        function clearEvents() {
            document.getElementById('events').innerHTML = '';
        }
        
        connectToChannel('tasks');
    </script>
</body>
</html>
"""


@app.get("/")
async def get():
    """Serve the WebSocket demo HTML page"""
    return HTMLResponse(html_template)


@app.websocket("/ws/{channel}")
async def websocket_endpoint(websocket: WebSocket, channel: str):
    """WebSocket endpoint for real-time updates"""
    await manager.connect(websocket, channel)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.send_personal(f"Echo: {data}", websocket)
    except:
        manager.disconnect(websocket, channel)


@app.post("/tasks", status_code=201)
async def create_task(
    title: str,
    description: Optional[str] = None,
    session: AsyncSession = Depends(get_db)
):
    """Create a new task - automatically broadcasts to connected WebSocket clients"""
    task = await Task.create(
        session,
        title=title,
        description=description
    )
    return task.to_response()


@app.get("/tasks")
async def list_tasks(session: AsyncSession = Depends(get_db)):
    """List all tasks"""
    tasks = await Task.all(session)
    return [task.to_response() for task in tasks]


@app.put("/tasks/{task_id}/toggle")
async def toggle_task(
    task_id: int,
    session: AsyncSession = Depends(get_db)
):
    """Toggle task completion status - broadcasts update to WebSocket clients"""
    task = await Task.get(session, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    await task.update_fields(session, completed=not task.completed)
    return task.to_response()


@app.delete("/tasks/{task_id}", status_code=204)
async def delete_task(
    task_id: int,
    session: AsyncSession = Depends(get_db)
):
    """Delete a task - broadcasts delete event to WebSocket clients"""
    deleted = await Task.delete_by_id(session, task_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Task not found")
    return None


@app.post("/users", status_code=201)
async def create_user(
    username: str,
    email: str,
    session: AsyncSession = Depends(get_db)
):
    """Create a new user - broadcasts to connected WebSocket clients"""
    user = await User.create(session, username=username, email=email)
    return user.to_response()


@app.get("/users")
async def list_users(session: AsyncSession = Depends(get_db)):
    """List all users"""
    users = await User.all(session)
    return [user.to_response() for user in users]


@app.get("/ws/stats")
async def websocket_stats():
    """Get WebSocket connection statistics"""
    return {
        "total_connections": manager.get_active_connections_count(),
        "channels": {
            channel: manager.get_active_connections_count(channel)
            for channel in manager.get_channels()
        },
        "active_channels": manager.get_channels()
    }


async def demo_websocket_manager():
    """
    Standalone demo of WebSocket manager functionality.
    """
    print("\n" + "=" * 60)
    print("WEBSOCKET MANAGER DEMO")
    print("=" * 60 + "\n")
    
    manager_demo = ConnectionManager()
    
    print("✅ ConnectionManager initialized\n")
    
    print("📋 Features:")
    print("   • Multi-channel support")
    print("   • Automatic model event broadcasting")
    print("   • Heartbeat/ping support")
    print("   • Subscription filtering")
    print("   • Lifecycle management\n")
    
    print("🔧 Integration with FastAPI ORM:")
    print("   manager.register_model_events(User)")
    print("   → Automatically broadcasts create/update/delete events\n")
    
    print("📡 WebSocket Channels:")
    print("   ws://localhost:5000/ws/tasks   → Task updates")
    print("   ws://localhost:5000/ws/users   → User updates")
    print("   ws://localhost:5000/ws/default → General updates\n")
    
    print("📊 Event Types:")
    print("   • create: New record created")
    print("   • update: Record modified")
    print("   • delete: Record removed")
    print("   • heartbeat: Keep-alive ping")
    print("   • connection: Client connected")
    print("   • disconnection: Client disconnected\n")
    
    print("=" * 60)
    print("To run the full demo:")
    print("   uvicorn examples.websocket_example:app --reload --port 5000")
    print("   Then open: http://localhost:5000")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    import sys
    
    print("""
╔══════════════════════════════════════════════════════════════╗
║         FASTAPI ORM - WEBSOCKET REAL-TIME UPDATES            ║
╚══════════════════════════════════════════════════════════════╝

This example demonstrates real-time database change notifications
using WebSocket integration with FastAPI ORM.

To run the full interactive demo:

    uvicorn examples.websocket_example:app --reload --port 5000

Then open your browser to:

    http://localhost:5000

Features demonstrated:
✅ Automatic event broadcasting on create/update/delete
✅ Multi-channel subscriptions
✅ Real-time UI updates
✅ Heartbeat/keep-alive
✅ Connection management
    """)
    
    if len(sys.argv) > 1 and sys.argv[1] == "--demo":
        asyncio.run(demo_websocket_manager())
    else:
        print("Run with --demo flag for standalone demo, or use uvicorn to start the server.")
