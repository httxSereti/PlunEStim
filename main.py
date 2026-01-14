# main.py (continued)
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import List

app = FastAPI()

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str):
        await self.active_connections[0].send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: int):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.broadcast(f"Client #{client_id} says: {data}")
            print(data)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcast(f"Client #{client_id} left the chat")
        
@app.get("/status")
async def get_status():
    await manager.broadcast("Called API")
    return {
        "status": "ready",
        "version": "0.1.0"
    }
# Serve a simple HTML client for testing
from fastapi.responses import HTMLResponse

@app.get("/")
async def get():
    return HTMLResponse("""
        <!DOCTYPE html>
        <html>
            <head>
                <title>Chat App</title>
            </head>
            <body>
                <h1>WebSocket Chat</h1>
                <form action="" onsubmit="sendMessage(event)">
                    <input type="text" id="messageText" autocomplete="off"/>
                    <button>Send</button>
                </form>
                <ul id='messages'>
                </ul>
                <script>
                    var ws = new WebSocket("ws://localhost:8000/ws/1"); // Connect as client 1
                    ws.onopen = function(event) {
                        console.log("WebSocket connection opened:", event);
                    };
                    ws.onmessage = function(event) {
                        var messages = document.getElementById('messages')
                        var message = document.createElement('li')
                        var content = document.createTextNode(event.data)
                        message.appendChild(content)
                        messages.appendChild(message)
                    };
                    ws.onclose = function(event) {
                        console.log("WebSocket connection closed:", event);
                    };
                    ws.onerror = function(event) {
                        console.error("WebSocket error observed:", event);
                    };
                    function sendMessage(event) {
                        var input = document.getElementById("messageText")
                        ws.send(input.value)
                        input.value = ''
                        event.preventDefault()
                    }
                </script>
            </body>
        </html>
    """)
    
if __name__ == "__main__":
    # # Start the Discord bot in a separate thread
    # bot_thread = threading.Thread(target=start_bot)
    # bot_thread.start()

    # Start FastAPI (main thread)
    uvicorn.run(app, host="0.0.0.0", port=8000)