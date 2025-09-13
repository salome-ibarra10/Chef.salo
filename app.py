import streamlit as st
from PIL import Image
import utils
import pyttsx3
import threading
import time
import tempfile
import os
import platform
from speech_components import create_speech_component, speak_with_browser, pause_browser_speech, resume_browser_speech, stop_browser_speech

# Intentar importar pygame, pero hacer que sea opcional
try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False
    print("Pygame no está disponible, usando solo pyttsx3")

# Verificar si estamos en un entorno de nube (Streamlit Cloud)
IS_CLOUD_ENV = os.getenv('STREAMLIT_SERVER_HEADLESS', 'false').lower() == 'true' or \
               'streamlit.io' in os.getenv('STREAMLIT_SERVER_BASE_URL', '') or \
               os.getenv('STREAMLIT_RUNTIME_ENVIRONMENT') == 'cloud' or \
               os.getenv('STREAMLIT_CLOUD') == 'true' or \
               not platform.system() == 'Windows'  # Asumir nube si no es Windows local

# Forzar modo nube para pruebas en Streamlit Cloud
if 'streamlit.app' in os.getenv('STREAMLIT_SERVER_BASE_URL', '') or \
   'share.streamlit.io' in os.getenv('STREAMLIT_SERVER_BASE_URL', ''):
    IS_CLOUD_ENV = True

print(f"Entorno de nube detectado: {IS_CLOUD_ENV}")
print(f"Sistema operativo: {platform.system()}")
print(f"STREAMLIT_SERVER_HEADLESS: {os.getenv('STREAMLIT_SERVER_HEADLESS')}")
print(f"STREAMLIT_SERVER_BASE_URL: {os.getenv('STREAMLIT_SERVER_BASE_URL')}")

st.set_page_config(layout="centered")

# Clase para gestionar el estado del audio
class AudioManager:
    def __init__(self):
        self.engine = None
        self.is_playing = False
        self.is_paused = False
        self.current_position = 0
        self.text_parts = []
        self.current_part = 0
        self.temp_files = []
        
    def init_engine(self):
        if self.engine is None:
            try:
                self.engine = pyttsx3.init()
                self.engine.setProperty('rate', 150)
                self.engine.setProperty('volume', 0.9)
            except Exception as e:
                print(f"Error al inicializar el motor de TTS: {e}")
                # Intentar con un motor alternativo si está disponible
                try:
                    import platform
                    if platform.system() == "Windows":
                        # Intentar con el motor SAPI específico de Windows
                        self.engine = pyttsx3.init('sapi5')
                    else:
                        # Intentar con espeak si está disponible
                        self.engine = pyttsx3.init('espeak')
                    self.engine.setProperty('rate', 150)
                    self.engine.setProperty('volume', 0.9)
                except Exception as e2:
                    print(f"Error al inicializar motor alternativo: {e2}")
                    # No lanzar excepción, sino retornar None y manejarlo
                    return None
        return self.engine
    
    def split_text_into_parts(self, text):
        """Divide el texto en partes manejables"""
        # Dividir por oraciones para mejor control
        sentences = text.replace('Paso', '|Paso').split('|')
        return [s.strip() for s in sentences if s.strip()]
    
    def prepare_recipe_text(self, recipe_data):
        """Prepara el texto completo de la receta"""
        text_parts = []
        
        # Título y descripción
        text_parts.append(f"Receta: {recipe_data['recipe_name']}. {recipe_data['description']}.")
        
        # Ingredientes
        ingredientes_text = "Ingredientes: "
        for ing in recipe_data["recipe_ingredients"]:
            ingredientes_text += f"{ing['quantity']} de {ing['name']}. "
        text_parts.append(ingredientes_text)
        
        # Instrucciones
        for i, step in enumerate(recipe_data["instructions"]):
            text_parts.append(f"Paso {i+1}: {step}.")
        
        return text_parts
    
    def play_audio_with_files(self, text_parts, start_part=0):
        """Reproduce audio usando archivos temporales (más confiable en Windows)"""
        try:
            self.text_parts = text_parts
            self.current_part = start_part
            self.is_playing = True
            self.is_paused = False

            # Usar pygame si está disponible, sino usar pyttsx3 directamente
            if PYGAME_AVAILABLE:
                # Inicializar pygame para reproducir archivos de audio
                pygame.mixer.init()

                for i in range(start_part, len(text_parts)):
                    if not self.is_playing:
                        break

                    while self.is_paused and self.is_playing:
                        time.sleep(0.1)

                    if self.is_playing:
                        self.current_part = i
                        try:
                            # Crear archivo de audio temporal
                            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
                            temp_filename = temp_file.name
                            temp_file.close()

                            # Generar archivo de audio
                            engine = pyttsx3.init()
                            engine.setProperty('rate', 150)
                            engine.setProperty('volume', 0.9)
                            engine.save_to_file(text_parts[i], temp_filename)
                            engine.runAndWait()

                            # Reproducir el archivo
                            pygame.mixer.music.load(temp_filename)
                            pygame.mixer.music.play()

                            # Esperar a que termine la reproducción
                            while pygame.mixer.music.get_busy() and self.is_playing and not self.is_paused:
                                time.sleep(0.1)

                            # Limpiar archivo temporal
                            try:
                                os.unlink(temp_filename)
                            except:
                                pass

                        except Exception as e:
                            print(f"Error al reproducir parte {i}: {e}")
                            # Intentar continuar con la siguiente parte
                            continue

                pygame.mixer.quit()
            else:
                # Fallback a pyttsx3 directo si pygame no está disponible
                self.play_audio_direct(text_parts, start_part)

            self.is_playing = False
            self.current_part = 0

        except Exception as e:
            print(f"Error al reproducir audio con archivos: {e}")
            self.is_playing = False
            self.is_paused = False
            self.current_part = 0
            if PYGAME_AVAILABLE:
                try:
                    pygame.mixer.quit()
                except:
                    pass

    def play_audio_direct(self, text_parts, start_part=0):
        """Reproduce audio directamente con pyttsx3 (sin archivos temporales)"""
        try:
            self.text_parts = text_parts
            self.current_part = start_part
            self.is_playing = True
            self.is_paused = False

            # Crear un nuevo motor para este hilo
            engine = pyttsx3.init()
            engine.setProperty('rate', 150)
            engine.setProperty('volume', 0.9)

            for i in range(start_part, len(text_parts)):
                if not self.is_playing:
                    break

                while self.is_paused and self.is_playing:
                    time.sleep(0.1)

                if self.is_playing:
                    self.current_part = i
                    try:
                        engine.say(text_parts[i])
                        engine.runAndWait()
                    except Exception as e:
                        print(f"Error al reproducir parte {i}: {e}")
                        # Intentar continuar con la siguiente parte
                        continue

            self.is_playing = False
            self.current_part = 0

        except Exception as e:
            print(f"Error al reproducir audio directo: {e}")
            self.is_playing = False
            self.is_paused = False
            self.current_part = 0

    def play_audio(self, text_parts, start_part=0):
        """Reproduce el audio desde una posición específica"""
        try:
            self.text_parts = text_parts
            self.current_part = start_part
            self.is_playing = True
            self.is_paused = False

            # En Windows, usar el método de archivos temporales si pygame está disponible
            if platform.system() == "Windows" and PYGAME_AVAILABLE:
                self.play_audio_with_files(text_parts, start_part)
            else:
                # Usar método directo para Windows sin pygame o para otros SO
                self.play_audio_direct(text_parts, start_part)

        except Exception as e:
            # No podemos usar st.error en un hilo, así que imprimimos el error
            print(f"Error al reproducir audio: {e}")
            self.is_playing = False
            self.is_paused = False
            self.current_part = 0
    
    def pause_audio(self):
        """Pausa la reproducción"""
        self.is_paused = True
    
    def resume_audio(self):
        """Reanuda la reproducción"""
        self.is_paused = False
    
    def stop_audio(self):
        """Detiene la reproducción"""
        self.is_playing = False
        self.is_paused = False
        self.current_part = 0
    
    def get_status(self):
        """Obtiene el estado actual"""
        if self.is_paused:
            return "pausado"
        elif self.is_playing:
            return "reproduciendo"
        else:
            return "detenido"

# Inicializar el gestor de audio en el estado de la sesión
if 'audio_manager' not in st.session_state:
    st.session_state.audio_manager = AudioManager()

def test_tts_engine():
    """Función para probar si el motor TTS está funcionando"""
    try:
        import pyttsx3
        import platform
        engine = None
        
        # Intentar diferentes motores según el sistema operativo
        if platform.system() == "Windows":
            try:
                engine = pyttsx3.init('sapi5')
            except:
                engine = pyttsx3.init()
        else:
            engine = pyttsx3.init()
            
        engine.setProperty('rate', 150)
        engine.setProperty('volume', 0.9)
        # Probar con un texto corto
        engine.say("Motor de audio funcionando correctamente")
        engine.runAndWait()
        return True
    except Exception as e:
        print(f"Error al probar motor TTS: {e}")
        return False

def main():
    # Inicializar componentes de JavaScript para Web Speech API
    create_speech_component()

    # --- Header Centrado ---
    with st.container():
        st.image("logo.png", width=200) # Logo centrado y con tamaño fijo
        st.title("Chef AI 🍳")
        st.subheader("Sube una foto de tus ingredientes y descubre una receta increíble.")

    st.divider()

    uploaded_file = st.file_uploader(
        "Arrastra y suelta una imagen aquí o haz clic para seleccionar", 
        type=["jpg", "png", "jpeg"]
    )
    
    meal_type = st.selectbox(
        "¿Para qué comida buscas una receta?",
        ("Desayuno", "Almuerzo", "Cena", "Postre", "Snack")
    )
    
    # Inicializar el estado de la sesión para almacenar los datos de la receta
    if 'recipe_data' not in st.session_state:
        st.session_state.recipe_data = None

    submit_button = st.button("Generar Receta")

    if submit_button and uploaded_file is not None:
        image = Image.open(uploaded_file)
        
        with st.spinner("Creando una receta única para ti... 👨‍🍳"):
            try:
                # 1. Generar la receta estructurada
                recipe_data = utils.get_structured_recipe(image, meal_type)
                
                if recipe_data:
                    # Guardar los datos en el estado de la sesión
                    st.session_state.recipe_data = recipe_data
                else:
                    st.error("No se pudo generar una receta. La respuesta de la IA no fue válida. Inténtalo de nuevo.")

            except Exception as e:
                st.error(f"Ocurrió un error inesperado: {e}")
    elif submit_button and uploaded_file is None:
        st.warning("Por favor, sube una imagen primero.")

    # Mostrar la receta si existe en el estado de la sesión
    if st.session_state.recipe_data:
        recipe_data = st.session_state.recipe_data
        
        # 2. Obtener una imagen para la receta
        recipe_image_url = utils.get_recipe_image(recipe_data["recipe_name"])

        # --- Mostrar la receta con el nuevo diseño vertical ---
        
        # Imagen del plato
        if recipe_image_url:
            st.image(recipe_image_url, caption=recipe_data["recipe_name"], use_container_width=True)
        
        # Título y descripción
        st.header(recipe_data["recipe_name"])
        st.write(recipe_data["description"])

        # Metadatos de la receta
        meta_cols = st.columns(5)
        with meta_cols[0]:
            st.info(f"**Prep:**\n{recipe_data['prep_time']}")
        with meta_cols[1]:
            st.info(f"**Cook:**\n{recipe_data['cook_time']}")
        with meta_cols[2]:
            st.info(f"**Servings:**\n{recipe_data['servings']}")
        with meta_cols[3]:
            st.info(f"**Category:**\n{recipe_data['category']}")
        with meta_cols[4]:
            st.success(f"**{recipe_data['difficulty']}**")

        st.divider()

        # Ingredientes
        st.subheader("🛒 Ingredientes")
        for ing in recipe_data["recipe_ingredients"]:
            st.checkbox(f"**{ing['quantity']}** {ing['name']}")

        st.divider()

        # Instrucciones
        st.subheader("👨‍🍳 Instrucciones")
        for i, step in enumerate(recipe_data["instructions"]):
            st.markdown(f"**Paso {i+1}:** {step}")

        st.divider()

        # Sección de controles de audio
        st.subheader("🔊 Controles de Audio")

        # Determinar qué sistema de audio usar
        if IS_CLOUD_ENV:
            # Usar Web Speech API para entornos de nube
            st.info("🌐 Usando síntesis de voz del navegador (Web Speech API)")

            # Verificar compatibilidad del navegador
            st.info("💡 **Compatibilidad:** Asegúrate de usar Chrome, Firefox, Safari o Edge para la mejor experiencia de voz.")

            # Crear columnas para los botones
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                # Botón de reproducir/iniciar
                if st.button("▶️ Reproducir", key="play_button_browser"):
                    try:
                        # Preparar el texto completo de la receta
                        text_parts = st.session_state.audio_manager.prepare_recipe_text(recipe_data)
                        full_text = " ".join(text_parts)

                        # Usar Web Speech API
                        speak_with_browser(full_text)
                        st.success("✅ Reproducción iniciada en el navegador")
                    except Exception as e:
                        st.error(f"❌ Error al iniciar la reproducción: {str(e)}")

            with col2:
                # Botón de pausar
                if st.button("⏸️ Pausar", key="pause_button_browser"):
                    pause_browser_speech()
                    st.info("⏸️ Reproducción pausada")

            with col3:
                # Botón de reanudar
                if st.button("▶️ Reanudar", key="resume_button_browser"):
                    resume_browser_speech()
                    st.success("▶️ Reproducción reanudada")

            with col4:
                # Botón de detener
                if st.button("⏹️ Detener", key="stop_button_browser"):
                    stop_browser_speech()
                    st.info("⏹️ Reproducción detenida")

            st.info("💡 **Nota:** La reproducción se controla desde el navegador. Asegúrate de que tu navegador soporte la Web Speech API.")

        else:
            # Usar pyttsx3 para entornos locales
            # Obtener el estado actual del audio
            audio_manager = st.session_state.audio_manager
            status = audio_manager.get_status()

            # Mostrar el estado actual
            status_colors = {
                "detenido": "⚫",
                "reproduciendo": "🟢",
                "pausado": "🟡"
            }
            st.info(f"Estado: {status_colors.get(status, '⚫')} **{status.upper()}**")

            # Botón de diagnóstico
            if st.button("🔧 Probar Audio", key="test_audio"):
                with st.spinner("Probando motor de audio..."):
                    if test_tts_engine():
                        st.success("✅ Motor de audio funcionando correctamente")
                    else:
                        st.error("❌ Error con el motor de audio. Verifica que pyttsx3 esté instalado correctamente.")

            # Crear columnas para los botones
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                # Botón de reproducir/iniciar
                if st.button("▶️ Reproducir", key="play_button",
                            disabled=audio_manager.is_playing and not audio_manager.is_paused):
                    try:
                        # Preparar el texto de la receta
                        text_parts = audio_manager.prepare_recipe_text(recipe_data)

                        # Detener cualquier reproducción anterior
                        audio_manager.stop_audio()

                        # Verificar que el motor TTS funcione antes de iniciar
                        if test_tts_engine():
                            # Iniciar reproducción en un hilo separado
                            threading.Thread(
                                target=audio_manager.play_audio,
                                args=(text_parts, 0),
                                daemon=True
                            ).start()
                            st.success("✅ Reproducción iniciada")
                            time.sleep(1)  # Pequeña pausa para que el usuario vea el mensaje
                            st.rerun()
                        else:
                            st.error("❌ El motor de audio no está disponible. Verifica que pyttsx3 esté instalado correctamente.")

                    except Exception as e:
                        st.error(f"❌ Error al iniciar la reproducción: {str(e)}")
                        st.info("💡 Consejo: En Windows, asegúrate de que el servicio de voz de Windows esté habilitado.")

            with col2:
                # Botón de pausar
                if st.button("⏸️ Pausar", key="pause_button",
                            disabled=not audio_manager.is_playing or audio_manager.is_paused):
                    audio_manager.pause_audio()
                    st.rerun()

            with col3:
                # Botón de reanudar
                if st.button("▶️ Reanudar", key="resume_button",
                            disabled=not audio_manager.is_paused):
                    audio_manager.resume_audio()
                    st.rerun()

            with col4:
                # Botón de detener
                if st.button("⏹️ Detener", key="stop_button",
                            disabled=not audio_manager.is_playing):
                    audio_manager.stop_audio()
                    st.rerun()

            # Información adicional sobre la reproducción
            if audio_manager.is_playing:
                if audio_manager.is_paused:
                    st.warning("⏸️ Reproducción pausada")
                else:
                    st.success(f"🟢 Reproduciendo... (Parte {audio_manager.current_part + 1} de {len(audio_manager.text_parts)})")
            elif status == "detenido":
                st.info("Listo para reproducir la receta")

        st.divider()

        # Consejos y Beneficios
        if recipe_data.get("pro_tips"):
            st.subheader("💡 Pro Tips")
            for tip in recipe_data["pro_tips"]:
                st.markdown(f"• {tip}")
        
        if recipe_data.get("nutritional_benefits"):
            st.subheader("🥗 Beneficios Nutricionales")
            for benefit in recipe_data["nutritional_benefits"]:
                st.markdown(f"• {benefit}")

if __name__ == "__main__":
    main()