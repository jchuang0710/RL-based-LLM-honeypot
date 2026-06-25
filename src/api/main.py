"""
FastAPI application for Honeypot and Attacker services
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict
import uuid
import json
import logging
from src.attacker.service import AttackerService
from src.honeypot.service import HoneypotService, HoneypotEnv
from src.shared import setting, InitializationManager
from src.shared.logging import configure_logging

configure_logging(log_file="api.log")
logger = logging.getLogger(__name__)

app = FastAPI(title="RL-based LLM Honeypot API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global services
llm_service = None
honeypot_service = None
dqn = None
device = None

# Session management
sessions: Dict[str, Dict] = {}


# Request/Response models
class CommandRequest(BaseModel):
    command: str
    session_id: Optional[str] = None


class CommandResponse(BaseModel):
    response: str
    session_id: str
    next_state: Optional[List[float]] = None
    reward: Optional[float] = None
    done: bool = False


class DetectHoneypotRequest(BaseModel):
    history: List[str]
    session_id: Optional[str] = None


class DetectHoneypotResponse(BaseModel):
    is_honeypot: bool
    session_id: str


class DetectStateRequest(BaseModel):
    command: str
    history: List[str]
    session_id: Optional[str] = None


class DetectStateResponse(BaseModel):
    tactic_id: int
    technique_id: int
    session_id: str


class GetTechniqueRequest(BaseModel):
    history: List[str]
    technique_set: Optional[List[str]] = None
    session_id: Optional[str] = None


class GetTechniqueResponse(BaseModel):
    technique: str
    commands: List[str]
    session_id: str


class SessionResponse(BaseModel):
    session_id: str
    system: str


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    global llm_service, honeypot_service, dqn, device
    
    logger.info("Initializing API services")
    
    # Determine mode from command line or default to train
    import sys
    import argparse
    mode = 'train'  # default
    
    # Parse command line arguments for mode
    parser = argparse.ArgumentParser(description='FastAPI Honeypot Server')
    parser.add_argument('--mode', type=str, choices=['train', 'test'], default='train',
                        help='Mode: train (training mode) or test (test mode with loaded model)')
    # Only parse known args to avoid conflicts with uvicorn
    args, _ = parser.parse_known_args()
    mode = args.mode
    
    # Initialize all services using InitializationManager
    init_manager = InitializationManager(
        model_name="../models/Llama-3.1-8B",
        model_type="local",
        mode=mode,
        ssh_port=2222
    )
    init_manager.initialize_all()
    
    # Get services from manager
    llm_service = init_manager.llm_service
    dqn = init_manager.dqn
    device = init_manager.device
    
    # Initialize honeypot service
    honeypot_service = HoneypotService(llm_service, dqn, setting.action_set)
    
    logger.info("API services initialized: system=%s device=%s", setting.system, device)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "RL-based LLM Honeypot API",
        "version": "1.0.0",
        "system": setting.system
    }


@app.get("/api/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy", "system": setting.system}


# Session management
@app.post("/api/session/create", response_model=SessionResponse)
async def create_session():
    """Create a new session"""
    session_id = str(uuid.uuid4())
    state = np.zeros(203)
    state[0] = 1
    sessions[session_id] = {
        "attacker": AttackerService(llm_service),
        "history": [],
        "state": state.tolist()
    }
    sessions[session_id]["attacker"].reset(['whoami'])
    return {"session_id": session_id, "system": setting.system}


@app.delete("/api/session/{session_id}")
async def delete_session(session_id: str):
    """Delete a session"""
    if session_id in sessions:
        del sessions[session_id]
        return {"message": "Session deleted"}
    raise HTTPException(status_code=404, detail="Session not found")


# Honeypot endpoints
@app.post("/api/honeypot/command", response_model=CommandResponse)
async def execute_command(request: CommandRequest):
    """
    Execute a command on the honeypot and get response.
    Uses RL agent to select action and LLM to generate response.
    """
    if not honeypot_service:
        raise HTTPException(status_code=503, detail="Honeypot service not initialized")
    
    # Get or create session
    if request.session_id and request.session_id in sessions:
        session = sessions[request.session_id]
        state = session["state"]
    else:
        # Create new session
        session_id = str(uuid.uuid4())
        sessions[session_id] = {
            "state": np.zeros(203),
            "history": []
        }
        sessions[session_id]["state"][0] = 1
        state = sessions[session_id]["state"]
        request.session_id = session_id
    
    # Process command using honeypot service
    response, next_state, reward, done, info = honeypot_service.process_command(
        request.command, state
    )
    
    # Update session
    sessions[request.session_id]["state"] = next_state.tolist()
    sessions[request.session_id]["history"].append(request.command)
    sessions[request.session_id]["history"].append(response)
    
    return CommandResponse(
        response=response,
        session_id=request.session_id,
        next_state=next_state.tolist(),
        reward=reward,
        done=done
    )


# Attacker endpoints
@app.post("/api/attacker/detect-honeypot", response_model=DetectHoneypotResponse)
async def detect_honeypot(request: DetectHoneypotRequest):
    """Detect if the system is a honeypot based on interaction history"""
    if not llm_service:
        raise HTTPException(status_code=503, detail="LLM service not initialized")
    
    # Get or create session
    if request.session_id and request.session_id in sessions:
        session_id = request.session_id
    else:
        session_id = str(uuid.uuid4())
        sessions[session_id] = {"attacker": AttackerService(llm_service), "history": []}
        sessions[session_id]["attacker"].reset(['whoami'])
    
    # Use history from request or session
    history = request.history if request.history else sessions[session_id]["history"]
    
    # Detect honeypot
    prompt_service = PromptService(setting.system)
    system_prompt = prompt_service.get_detector_prompt()
    message = ""
    if len(history) > 0:
        for i, item in enumerate(history):
            if i % 2 == 0:
                message = message + "input: " + item + "\n"
            else:
                message = message + "output: " + item + "\n"
    
    response = llm_service.generate(system_prompt, message, [], max_tokens=5, temperature=0.01, top_p=0.8)
    is_honeypot = response.strip().lower() == "yes"
    
    return DetectHoneypotResponse(is_honeypot=is_honeypot, session_id=session_id)


@app.post("/api/attacker/detect-state", response_model=DetectStateResponse)
async def detect_state(request: DetectStateRequest):
    """Detect current MITRE tactic and technique based on command"""
    if not llm_service:
        raise HTTPException(status_code=503, detail="LLM service not initialized")
    
    # Get or create session
    if request.session_id and request.session_id in sessions:
        session_id = request.session_id
    else:
        session_id = str(uuid.uuid4())
        sessions[session_id] = {"attacker": AttackerService(llm_service), "history": []}
        sessions[session_id]["attacker"].reset(['whoami'])
    
    # Use history from request or session
    history = request.history if request.history else sessions[session_id]["history"]
    
    # Detect state
    prompt_service = PromptService(setting.system)
    system_prompt = prompt_service.get_detector_state_prompt()
    message = ""
    if len(history) > 0:
        for i, item in enumerate(history):
            if i % 2 == 0:
                message = message + "past_input: " + item + "\n"
    
    user_prompt = message + "current command: " + str(request.command) + "\n"
    
    # Use fine-tuned model for state detection if OpenAI
    model_override = None
    if llm_service.model_type == "openai":
        model_override = "ft:gpt-4o-mini-2024-07-18:personal:detect-ttp-atomic-0924:AAqZyEOo"
    
    import time
    response = []
    while len(response) < 2:
        resp = llm_service.generate(system_prompt, user_prompt, [], max_tokens=20, temperature=0.01, top_p=0.8, model_override=model_override)
        response = resp.split(' ')
        if len(response) < 2:
            time.sleep(1)
            continue
    
    # Translate IDs to indices
    tacticID = ['TA0001','TA0002', 'TA0003', 'TA0004', 'TA0005', 'TA0006', 'TA0007', 'TA0008', 'TA0009', 'TA0011', 'TA0010', 'TA0040']
    techniqueID = ['T1548', 'T1134', 'T1531', 'T1087', 'T1098', 'T1650', 'T1583', 'T1595', 'T1557', 'T1071', 'T1010', 'T1560', 'T1123', 'T1119', 'T1020', 'T1197', 'T1547', 'T1037', 'T1176', 'T1217', 'T1185', 'T1110', 'T1612', 'T1115', 'T1651', 'T1580', 'T1538', 'T1526', 'T1619', 'T1059', 'T1092', 'T1586', 'T1554', 'T1584', 'T1609', 'T1613', 'T1659', 'T1136', 'T1543', 'T1555', 'T1485', 'T1132', 'T1486', 'T1530', 'T1602', 'T1213', 'T1005', 'T1039', 'T1025', 'T1565', 'T1001', 'T1074', 'T1030', 'T1622', 'T1491', 'T1140', 'T1610', 'T1587', 'T1652', 'T1006', 'T1561', 'T1484', 'T1482', 'T1189', 'T1568', 'T1114', 'T1573', 'T1499', 'T1611', 'T1585', 'T1546', 'T1480', 'T1048', 'T1041', 'T1011', 'T1052', 'T1567', 'T1190', 'T1203', 'T1212', 'T1211', 'T1068', 'T1210', 'T1133', 'T1008', 'T1083', 'T1222', 'T1657', 'T1495', 'T1187', 'T1606', 'T1592', 'T1589', 'T1590', 'T1591', 'T1615', 'T1200', 'T1564', 'T1665', 'T1574', 'T1562', 'T1656', 'T1525', 'T1070', 'T1202', 'T1105', 'T1490', 'T1056', 'T1559', 'T1534', 'T1570', 'T1654', 'T1036', 'T1556', 'T1578', 'T1112', 'T1601', 'T1111', 'T1621', 'T1104', 'T1106', 'T1599', 'T1498', 'T1046', 'T1135', 'T1040', 'T1095', 'T1571', 'T1027', 'T1588', 'T1137', 'T1003', 'T1201', 'T1120', 'T1069', 'T1566', 'T1598', 'T1647', 'T1653', 'T1542', 'T1057', 'T1055', 'T1572', 'T1090', 'T1012', 'T1620', 'T1219', 'T1563', 'T1021', 'T1018', 'T1091', 'T1496', 'T1207', 'T1014', 'T1053', 'T1029', 'T1113', 'T1597', 'T1596', 'T1593', 'T1594', 'T1505', 'T1648', 'T1489', 'T1129', 'T1072', 'T1518', 'T1608', 'T1528', 'T1649', 'T1558', 'T1539', 'T1553', 'T1195', 'T1218', 'T1082', 'T1614', 'T1016', 'T1049', 'T1033', 'T1216', 'T1007', 'T1569', 'T1529', 'T1124', 'T1080', 'T1221', 'T1205', 'T1537', 'T1127', 'T1199', 'T1552', 'T1535', 'T1550', 'T1204', 'T1078', 'T1125', 'T1497', 'T1600', 'T1102', 'T1047', 'T1220']
    
    tactic = response[0]
    technique = response[1]
    if len(technique) > 5:
        technique = technique[:5]
    
    tactic_id = tacticID.index(tactic) if tactic in tacticID else 1
    technique_id = techniqueID.index(technique) if technique in techniqueID else 1
    
    return DetectStateResponse(tactic_id=tactic_id, technique_id=technique_id, session_id=session_id)


@app.post("/api/attacker/get-technique", response_model=GetTechniqueResponse)
async def get_technique(request: GetTechniqueRequest):
    """Get next attack technique based on interaction history"""
    if not llm_service:
        raise HTTPException(status_code=503, detail="LLM service not initialized")
    
    # Get or create session
    if request.session_id and request.session_id in sessions:
        attacker = sessions[request.session_id]["attacker"]
        session_id = request.session_id
    else:
        session_id = str(uuid.uuid4())
        attacker = AttackerService(llm_service)
        attacker.reset(['whoami'])
        sessions[session_id] = {"attacker": attacker, "history": []}
    
    # Use history from request or session
    history = request.history if request.history else sessions[session_id]["history"]
    
    # Get next attack technique
    next_technique = attacker.get_next_attack_technique(history, request.technique_set)
    commands = attacker.get_commands_for_technique(next_technique)
    
    return GetTechniqueResponse(
        technique=next_technique,
        commands=commands,
        session_id=session_id
    )


# WebSocket endpoint for real-time SSH-like interaction
@app.websocket("/api/honeypot/ws")
async def websocket_honeypot(websocket: WebSocket):
    """WebSocket endpoint for real-time honeypot interaction"""
    await websocket.accept()
    session_id = str(uuid.uuid4())
    state = np.zeros(203)
    state[0] = 1
    sessions[session_id] = {
        "state": state.tolist(),
        "history": []
    }
    
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get("type") == "command":
                command = message.get("command", "")
                
                # Process command
                state = np.array(sessions[session_id]["state"])
                response, next_state, reward, done, info = honeypot_service.process_command(
                    command, state
                )
                
                # Update session
                sessions[session_id]["state"] = next_state.tolist()
                sessions[session_id]["history"].append(command)
                sessions[session_id]["history"].append(response)
                
                # Send response
                await websocket.send_json({
                    "type": "response",
                    "response": response,
                    "done": done,
                    "info": info
                })
            
            elif message.get("type") == "close":
                break
                
    except WebSocketDisconnect:
        pass
    finally:
        if session_id in sessions:
            del sessions[session_id]


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
