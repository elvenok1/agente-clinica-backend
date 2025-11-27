from dotenv import load_dotenv
import logging
from livekit import agents
from livekit.agents import AgentSession, Agent, RoomInputOptions
from livekit.plugins import (
    openai,
    noise_cancellation,
    bey
)
from tools import unblock_user, send_email
from prompts import AGENT_INSTRUCTIONS
import os
from livekit.agents import BackgroundAudioPlayer, AudioConfig, BuiltinAudioClip

load_dotenv(".env.local")

class Assistant(Agent):
    def __init__(self) -> None:
        super().__init__(instructions=AGENT_INSTRUCTIONS,
        tools=[unblock_user, send_email])

async def entrypoint(ctx: agents.JobContext):
    # Conectamos con el contexto del trabajo para detectar cuando cierra
    await ctx.connect()

    session = AgentSession(
        llm=openai.realtime.RealtimeModel(
            api_key="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",
            voice="coral"
        )
    )

    # Configuración del Avatar
    avatar = bey.AvatarSession(
        avatar_id=os.getenv("BEY_AVATAR_ID"), 
    )

    # Parche de URL para WSS (Corrección de conexión)
    ws_url = os.getenv("LIVEKIT_URL")
    if ws_url:
        if ws_url.startswith("https"): ws_url = ws_url.replace("https", "wss")
        elif ws_url.startswith("http"): ws_url = ws_url.replace("http", "ws")
        # Iniciamos el avatar con la URL corregida
        await avatar.start(session, room=ctx.room, livekit_url=ws_url)
    else:
        await avatar.start(session, room=ctx.room)

    # Iniciamos la sesión del agente
    await session.start(
        room=ctx.room,
        agent=Assistant(),
        room_input_options=RoomInputOptions(
            noise_cancellation=noise_cancellation.BVC(),
            video_enabled=True,
        ),
    )

    # Audio de fondo (Teclado)
    background_audio = BackgroundAudioPlayer(
        thinking_sound=[
            AudioConfig(BuiltinAudioClip.KEYBOARD_TYPING, volume=0.5),
            AudioConfig(BuiltinAudioClip.KEYBOARD_TYPING2, volume=0.5),
        ],
    )
    await background_audio.start(room=ctx.room, agent_session=session)

    # Saludo Inicial
    await session.generate_reply(
        instructions="Saluda al usuario en español. Di: 'Hola, soy Natalia de la Clínica del Doctor Gary Ortega. ¿En qué cambio estético estás interesada hoy?'"
    )

    # --- CORRECCIÓN CRÍTICA ---
    # Esperamos a que el usuario se desconecte o el trabajo termine.
    # Cuando esto pase, el script limpiará los recursos automáticamente.
    # Sin esta línea, el script termina prematuramente o se queda colgado.
    await ctx.wait_for_shutdown()

if __name__ == "__main__":
    # Inicializamos con logs para ver si hay errores al desconectar
    logging.basicConfig(level=logging.INFO)
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))
