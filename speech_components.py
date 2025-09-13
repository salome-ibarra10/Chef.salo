import streamlit as st
import streamlit.components.v1 as components

def create_speech_component():
    """Crea un componente de JavaScript para la Web Speech API"""

    # JavaScript para la Web Speech API
    speech_js = """
    <script>
    let speechSynthesis = window.speechSynthesis;
    let currentUtterance = null;
    let isPlaying = false;
    let isPaused = false;

    // Función para verificar si la Web Speech API está disponible
    function isSpeechSupported() {
        return 'speechSynthesis' in window;
    }

    // Función para verificar voces disponibles
    function getAvailableVoices() {
        return speechSynthesis.getVoices();
    }

    // Función para seleccionar la mejor voz en español
    function selectSpanishVoice() {
        const voices = getAvailableVoices();
        // Buscar voz en español
        let spanishVoice = voices.find(voice =>
            voice.lang.startsWith('es') ||
            voice.name.toLowerCase().includes('spanish') ||
            voice.name.toLowerCase().includes('español')
        );
        return spanishVoice || voices[0]; // Usar primera voz disponible si no hay española
    }

    // Función para hablar texto
    function speakText(text, onStart, onEnd, onError) {
        if (!isSpeechSupported()) {
            onError('La Web Speech API no está disponible en este navegador');
            return;
        }

        // Detener cualquier reproducción anterior
        stopSpeech();

        // Crear nueva utterance
        currentUtterance = new SpeechSynthesisUtterance(text);

        // Seleccionar voz en español
        const spanishVoice = selectSpanishVoice();
        if (spanishVoice) {
            currentUtterance.voice = spanishVoice;
        }

        // Configurar propiedades
        currentUtterance.rate = 0.8;  // Velocidad más lenta para mejor comprensión
        currentUtterance.pitch = 1;   // Tono normal
        currentUtterance.volume = 0.9; // Volumen más alto
        currentUtterance.lang = spanishVoice ? spanishVoice.lang : 'es-ES';

        // Configurar eventos
        currentUtterance.onstart = function() {
            isPlaying = true;
            isPaused = false;
            console.log('Speech started');
            if (onStart) onStart();
        };

        currentUtterance.onend = function() {
            isPlaying = false;
            isPaused = false;
            console.log('Speech ended');
            if (onEnd) onEnd();
        };

        currentUtterance.onerror = function(event) {
            isPlaying = false;
            isPaused = false;
            console.error('Speech error:', event.error);
            if (onError) onError('Error en la síntesis de voz: ' + event.error);
        };

        // Pequeño delay para asegurar que las voces estén cargadas
        setTimeout(() => {
            speechSynthesis.speak(currentUtterance);
        }, 100);
    }

    // Función para pausar
    function pauseSpeech() {
        if (speechSynthesis && speechSynthesis.pause && isPlaying && !isPaused) {
            speechSynthesis.pause();
            isPaused = true;
            console.log('Speech paused');
        }
    }

    // Función para reanudar
    function resumeSpeech() {
        if (speechSynthesis && speechSynthesis.resume && isPaused) {
            speechSynthesis.resume();
            isPaused = false;
            console.log('Speech resumed');
        }
    }

    // Función para detener
    function stopSpeech() {
        if (speechSynthesis) {
            speechSynthesis.cancel();
        }
        currentUtterance = null;
        isPlaying = false;
        isPaused = false;
        console.log('Speech stopped');
    }

    // Función para obtener estado
    function getSpeechStatus() {
        if (isPaused) return 'paused';
        if (isPlaying) return 'playing';
        return 'stopped';
    }

    // Inicializar voces cuando estén disponibles
    if (speechSynthesis.onvoiceschanged !== undefined) {
        speechSynthesis.onvoiceschanged = function() {
            console.log('Voices loaded:', getAvailableVoices().length);
        };
    }

    // Exponer funciones al ámbito global para que Streamlit pueda acceder
    window.speechAPI = {
        speakText: speakText,
        pauseSpeech: pauseSpeech,
        resumeSpeech: resumeSpeech,
        stopSpeech: stopSpeech,
        getSpeechStatus: getSpeechStatus,
        isSpeechSupported: isSpeechSupported,
        getAvailableVoices: getAvailableVoices
    };

    console.log('Speech API initialized. Supported:', isSpeechSupported());
    </script>
    """

    # HTML del componente
    html_content = f"""
    <div id="speech-component">
        {speech_js}
        <div id="speech-status" style="display: none;">stopped</div>
    </div>
    """

    # Renderizar el componente
    components.html(html_content, height=0)

def speak_with_browser(text):
    """Función para hablar usando el navegador (Web Speech API)"""
    # JavaScript para ejecutar la síntesis de voz
    js_code = f"""
    <script>
    if (window.speechAPI && window.speechAPI.isSpeechSupported()) {{
        window.speechAPI.speakText(
            `{text}`,
            function() {{
                console.log('Speech started');
            }},
            function() {{
                console.log('Speech ended');
            }},
            function(error) {{
                console.error('Speech error:', error);
            }}
        );
    }} else {{
        console.error('Web Speech API not supported');
    }}
    </script>
    """

    components.html(js_code, height=0)

def pause_browser_speech():
    """Pausar la reproducción en el navegador"""
    js_code = """
    <script>
    if (window.speechAPI) {
        window.speechAPI.pauseSpeech();
    }
    </script>
    """
    components.html(js_code, height=0)

def resume_browser_speech():
    """Reanudar la reproducción en el navegador"""
    js_code = """
    <script>
    if (window.speechAPI) {
        window.speechAPI.resumeSpeech();
    }
    </script>
    """
    components.html(js_code, height=0)

def stop_browser_speech():
    """Detener la reproducción en el navegador"""
    js_code = """
    <script>
    if (window.speechAPI) {
        window.speechAPI.stopSpeech();
    }
    </script>
    """
    components.html(js_code, height=0)

def get_browser_speech_status():
    """Obtener el estado de la reproducción (esta función es limitada en Streamlit)"""
    # En Streamlit es difícil obtener valores de vuelta desde JavaScript
    # Por eso usamos un enfoque basado en botones y estado de sesión
    return "unknown"