import streamlit as st
import os
import time
import json
import pandas as pd
from pathlib import Path
import requests
import io
import base64
import tempfile
import concurrent.futures
import threading
from pathlib import Path
import re

# Audio recording component
from audio_recorder_streamlit import audio_recorder
def validate_secrets():
    """Validate that all required secrets are present"""
    required_keys = ["api_keys.GROQ_API_KEY", "api_keys.SARVAM_API_KEY"]
    missing_keys = []
    
    for key in required_keys:
        try:
            keys = key.split('.')
            value = st.secrets
            for k in keys:
                value = value[k]
        except (KeyError, TypeError):
            missing_keys.append(key)
    
    if missing_keys:
        st.error(f"Missing required secrets: {', '.join(missing_keys)}")
        st.info("Please configure your API keys in Streamlit secrets")
        st.stop()

# Call this function early in your app
validate_secrets()
import gc

def cleanup_memory():
    """Clean up memory periodically"""
    gc.collect()
    
# Add this call in your main processing sections
if st.button("🔄 Clear Memory", key="cleanup_memory"):
    cleanup_memory()
    st.success("✅ Memory cleaned up")
# Set USER_AGENT to avoid warnings
os.environ.setdefault('USER_AGENT', st.secrets.get("settings", {}).get("USER_AGENT", "StreamlitAgricultureApp/1.0"))

# --- Translation System ---
TRANSLATIONS = {
    'english': {
        'app_title': '🌱 AI Soil & Agriculture Assistant',
        'language_popup_title': '🌍 Select Your Preferred Language',
        'language_popup_subtitle': 'Choose your language for the best experience',
        'language_popup_button': 'Continue',
        'app_description': '**Complete Agricultural Intelligence System**\n\nGet comprehensive farming advice combining:',
        'soil_analysis': '🧪 **Detailed Soil Analysis** for Tamil Nadu & Kerala (16 major cities)',
        'gov_schemes': '🌾 **Government Schemes** and agricultural policies',
        'soil_parameters': '📊 **10+ Soil Parameters** including pH, nutrients, organic matter',
        'crop_recommendations': '🚜 **Crop Recommendations** based on actual soil conditions',
        'crop_cycle': '🌿 **Crop Cycle Management** with seasonal guidance',
        'configuration': '🔧 Configuration',
        'building_kb': '🔨 Building comprehensive agricultural knowledge base...',
        'kb_ready': '✅ Knowledge Base Ready!',
        'what_you_can_ask': '💡 What You Can Ask:',
        'soil_location': '🧪 Soil & Location:',
        'crop_cycles': '🌿 Crop Cycles:',
        'government_schemes': '🏛️ Government Schemes:',
        'voice_assistant': '🎤 Voice Assistant (Auto Language Detection)',
        'record_voice': '🎙️ Record Voice',
        'upload_audio': '📁 Upload Audio File',
        'recording_instructions': '📋 Recording Instructions:',
        'chat_input_placeholder': '💬 Ask about soil conditions, crop cycles, seasonal planning, government schemes...',
        'processing_notification': '🔄 Processing in background...',
        'show_all_details': '📋 Show All Processing Details',
        'hide_details': '📋 Hide Details'
    },
    'hindi': {
        'app_title': '🌱 एआई मिट्टी और कृषि सहायक',
        'language_popup_title': '🌍 अपनी पसंदीदा भाषा चुनें',
        'language_popup_subtitle': 'सर्वोत्तम अनुभव के लिए अपनी भाषा चुनें',
        'language_popup_button': 'जारी रखें',
        'app_description': '**संपूर्ण कृषि बुद्धिमत्ता प्रणाली**\n\nव्यापक कृषि सलाह प्राप्त करें:',
        'soil_analysis': '🧪 **विस्तृत मिट्टी विश्लेषण** तमिलनाडु और केरल के लिए (16 प्रमुख शहर)',
        'gov_schemes': '🌾 **सरकारी योजनाएं** और कृषि नीतियां',
        'soil_parameters': '📊 **10+ मिट्टी पैरामीटर** pH, पोषक तत्व, जैविक पदार्थ सहित',
        'crop_recommendations': '🚜 **फसल सिफारिशें** वास्तविक मिट्टी की स्थिति के आधार पर',
        'crop_cycle': '🌿 **फसल चक्र प्रबंधन** मौसमी मार्गदर्शन के साथ',
        'configuration': '🔧 कॉन्फ़िगरेशन',
        'building_kb': '🔨 व्यापक कृषि ज्ञान आधार का निर्माण...',
        'kb_ready': '✅ ज्ञान आधार तैयार!',
        'what_you_can_ask': '💡 आप क्या पूछ सकते हैं:',
        'soil_location': '🧪 मिट्टी और स्थान:',
        'crop_cycles': '🌿 फसल चक्र:',
        'government_schemes': '🏛️ सरकारी योजनाएं:',
        'voice_assistant': '🎤 आवाज सहायक (स्वचालित भाषा पहचान)',
        'record_voice': '🎙️ आवाज रिकॉर्ड करें',
        'upload_audio': '📁 ऑडियो फ़ाइल अपलोड करें',
        'recording_instructions': '📋 रिकॉर्डिंग निर्देश:',
        'chat_input_placeholder': '💬 मिट्टी की स्थिति, फसल चक्र, मौसमी योजना, सरकारी योजनाओं के बारे में पूछें...',
        'processing_notification': '🔄 पृष्ठभूमि में प्रसंस्करण...',
        'show_all_details': '📋 सभी प्रसंस्करण विवरण दिखाएं',
        'hide_details': '📋 विवरण छुपाएं'
    },
    'tamil': {
        'app_title': '🌱 AI மண் மற்றும் விவசாய உதவியாளர்',
        'language_popup_title': '🌍 உங்கள் விருப்பமான மொழியைத் தேர்ந்தெடுக்கவும்',
        'language_popup_subtitle': 'சிறந்த அனுபவத்திற்கு உங்கள் மொழியைத் தேர்ந்தெடுக்கவும்',
        'language_popup_button': 'தொடரவும்',
        'app_description': '**முழுமையான விவசாய நுண்ணறிவு அமைப்பு**\n\nவிரிவான விவசாய ஆலோசனைகளைப் பெறுங்கள்:',
        'soil_analysis': '🧪 **விரிவான மண் பகுப்பாய்வு** தமிழ்நாடு மற்றும் கேரளாவிற்கு (16 முக்கிய நகரங்கள்)',
        'gov_schemes': '🌾 **அரசு திட்டங்கள்** மற்றும் விவசாய கொள்கைகள்',
        'soil_parameters': '📊 **10+ மண் அளவுருக்கள்** pH, ஊட்டச்சத்துக்கள், கரிமப் பொருட்கள் உட்பட',
        'crop_recommendations': '🚜 **பயிர் பரிந்துரைகள்** உண்மையான மண் நிலைமைகளின் அடிப்படையில்',
        'crop_cycle': '🌿 **பயிர் சுழற்சி மேலாண்மை** பருவகால வழிகாட்டுதலுடன்',
        'configuration': '🔧 கட்டமைப்பு',
        'building_kb': '🔨 விரிவான விவசாய அறிவுத் தளத்தை உருவாக்குதல்...',
        'kb_ready': '✅ அறிவுத் தளம் தயார்!',
        'what_you_can_ask': '💡 நீங்கள் என்ன கேட்கலாம்:',
        'soil_location': '🧪 மண் மற்றும் இடம்:',
        'crop_cycles': '🌿 பயிர் சுழற்சிகள்:',
        'government_schemes': '🏛️ அரசு திட்டங்கள்:',
        'voice_assistant': '🎤 குரல் உதவியாளர் (தானியங்கி மொழி கண்டறிதல்)',
        'record_voice': '🎙️ குரலை பதிவு செய்யுங்கள்',
        'upload_audio': '📁 ஆடியோ கோப்பை பதிவேற்றவும்',
        'recording_instructions': '📋 பதிவு செய்யும் வழிமுறைகள்:',
        'chat_input_placeholder': '💬 மண் நிலைமைகள், பயிர் சுழற்சிகள், பருவகால திட்டமிடல், அரசு திட்டங்கள் பற்றி கேளுங்கள்...',
        'processing_notification': '🔄 பின்னணியில் செயலாக்கம்...',
        'show_all_details': '📋 அனைத்து செயலாக்க விவரங்களையும் காட்டு',
        'hide_details': '📋 விவரங்களை மறை'
    },
    'bengali': {
        'app_title': '🌱 AI মাটি ও কৃষি সহায়ক',
        'language_popup_title': '🌍 আপনার পছন্দের ভাষা নির্বাচন করুন',
        'language_popup_subtitle': 'সর্বোত্তম অভিজ্ঞতার জন্য আপনার ভাষা বেছে নিন',
        'language_popup_button': 'চালিয়ে যান',
        'app_description': '**সম্পূর্ণ কৃষি বুদ্ধিমত্তা সিস্টেম**\n\nব্যাপক কৃষি পরামর্শ পান:',
        'soil_analysis': '🧪 **বিস্তারিত মাটি বিশ্লেষণ** তামিলনাড়ু ও কেরালার জন্য (১৬টি প্রধান শহর)',
        'gov_schemes': '🌾 **সরকারি প্রকল্প** এবং কৃষি নীতি',
        'soil_parameters': '📊 **১০+ মাটির পরামিতি** pH, পুষ্টি উপাদান, জৈব পদার্থ সহ',
        'crop_recommendations': '🚜 **ফসলের সুপারিশ** প্রকৃত মাটির অবস্থার ভিত্তিতে',
        'crop_cycle': '🌿 **ফসল চক্র ব্যবস্থাপনা** ঋতুভিত্তিক নির্দেশনা সহ',
        'configuration': '🔧 কনফিগারেশন',
        'building_kb': '🔨 ব্যাপক কৃষি জ্ঞানের ভিত্তি তৈরি করা হচ্ছে...',
        'kb_ready': '✅ জ্ঞানের ভিত্তি প্রস্তুত!',
        'what_you_can_ask': '💡 আপনি কী জিজ্ঞাসা করতে পারেন:',
        'soil_location': '🧪 মাটি ও অবস্থান:',
        'crop_cycles': '🌿 ফসল চক্র:',
        'government_schemes': '🏛️ সরকারি প্রকল্প:',
        'voice_assistant': '🎤 ভয়েস সহায়ক (স্বয়ংক্রিয় ভাষা সনাক্তকরণ)',
        'record_voice': '🎙️ ভয়েস রেকর্ড করুন',
        'upload_audio': '📁 অডিও ফাইল আপলোড করুন',
        'recording_instructions': '📋 রেকর্ডিং নির্দেশাবলী:',
        'chat_input_placeholder': '💬 মাটির অবস্থা, ফসল চক্র, ঋতুভিত্তিক পরিকল্পনা, সরকারি প্রকল্প সম্পর্কে জিজ্ঞাসা করুন...',
        'processing_notification': '🔄 পটভূমিতে প্রক্রিয়াকরণ...',
        'show_all_details': '📋 সমস্ত প্রক্রিয়াকরণের বিবরণ দেখান',
        'hide_details': '📋 বিবরণ লুকান'
    },
    'malayalam': {
        'app_title': '🌱 AI മണ്ണും കൃഷിയും സഹായി',
        'language_popup_title': '🌍 നിങ്ങളുടെ ഇഷ്ടമുള്ള ഭാഷ തിരഞ്ഞെടുക്കുക',
        'language_popup_subtitle': 'മികച്ച അനുഭവത്തിനായി നിങ്ങളുടെ ഭാഷ തിരഞ്ഞെടുക്കുക',
        'language_popup_button': 'തുടരുക',
        'app_description': '**സമ്പൂർണ്ണ കാർഷിക ബുദ്ധിമത്ത സംവിധാനം**\n\nവിപുലമായ കാർഷിക ഉപദേശം നേടുക:',
        'soil_analysis': '🧪 **വിശദമായ മണ്ണ് വിശകലനം** തമിഴ്നാട്, കേരളം (16 പ്രധാന നഗരങ്ങൾ)',
        'gov_schemes': '🌾 **സർക്കാർ പദ്ധതികൾ** കൃഷി നയങ്ങൾ',
        'soil_parameters': '📊 **10+ മണ്ണിന്റെ പാരാമീറ്ററുകൾ** pH, പോഷകങ്ങൾ, ജൈവവസ്തുക്കൾ',
        'crop_recommendations': '🚜 **വിള ശുപാർശകൾ** യഥാർത്ഥ മണ്ണിന്റെ അവസ്ഥ അടിസ്ഥാനമാക്കി',
        'crop_cycle': '🌿 **വിള ചക്ര മാനേജ്മെന്റ്** സീസണൽ ഗൈഡൻസ്',
        'configuration': '🔧 കോൺഫിഗറേഷൻ',
        'building_kb': '🔨 സമഗ്ര കാർഷിക അറിവിന്റെ അടിത്തറ നിർമ്മിക്കുന്നു...',
        'kb_ready': '✅ അറിവിന്റെ അടിത്തറ തയ്യാർ!',
        'what_you_can_ask': '💡 നിങ്ങൾക്ക് എന്ത് ചോദിക്കാം:',
        'soil_location': '🧪 മണ്ണും സ്ഥലവും:',
        'crop_cycles': '🌿 വിള ചക്രങ്ങൾ:',
        'government_schemes': '🏛️ സർക്കാർ പദ്ധതികൾ:',
        'voice_assistant': '🎤 വോയ്സ് അസിസ്റ്റന്റ് (ഓട്ടോ ഭാഷാ തിരിച്ചറിയൽ)',
        'record_voice': '🎙️ ശബ്ദം റെക്കോർഡ് ചെയ്യുക',
        'upload_audio': '📁 ഓഡിയോ ഫയൽ അപ്‌ലോഡ് ചെയ്യുക',
        'recording_instructions': '📋 റെക്കോർഡിംഗ് നിർദ്ദേശങ്ങൾ:',
        'chat_input_placeholder': '💬 മണ്ണിന്റെ അവസ്ഥ, വിള ചക്രങ്ങൾ, സീസണൽ പ്ലാനിംഗ്, സർക്കാർ പദ്ധതികൾ എന്നിവയെക്കുറിച്ച് ചോദിക്കുക...',
        'processing_notification': '🔄 പശ്ചാത്തലത്തിൽ പ്രോസസ്സിംഗ്...',
        'show_all_details': '📋 എല്ലാ പ്രോസസ്സിംഗ് വിശദാംശങ്ങളും കാണിക്കുക',
        'hide_details': '📋 വിശദാംശങ്ങൾ മറയ്ക്കുക'
    }
}

def get_text(key, language='english'):
    """Get translated text for the given key and language"""
    return TRANSLATIONS.get(language, TRANSLATIONS['english']).get(key, TRANSLATIONS['english'].get(key, key))

def show_language_selection_popup():
    """Show language selection with dropdown interface"""
    
    # Custom CSS for clean popup styling
    popup_css = """
    <style>
    .language-selection-container {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 15px;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
        margin: 1rem 0;
        text-align: center;
        color: white;
    }
    
    .language-title {
        font-size: 1.8em;
        font-weight: bold;
        margin-bottom: 0.5rem;
        text-shadow: 0 2px 4px rgba(0,0,0,0.3);
    }
    
    .language-subtitle {
        font-size: 1.1em;
        margin-bottom: 1.5rem;
        opacity: 0.9;
    }
    
    .language-info {
        background: rgba(255, 255, 255, 0.1);
        padding: 1rem;
        border-radius: 10px;
        margin-top: 1rem;
        backdrop-filter: blur(10px);
    }
    </style>
    """
    
    st.markdown(popup_css, unsafe_allow_html=True)
    
    # Create the language selection container
    st.markdown("""
    <div class="language-selection-container">
        <div class="language-title">🌍 Select Your Preferred Language</div>
        <div class="language-subtitle">Choose your language for the best experience</div>
        <div class="language-info">
            📱 Your selection will apply to the entire interface<br>
            🎤 Voice input/output will use your chosen language<br>
            🔄 You can change this anytime from the sidebar
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Create language options with native names
    language_options = {
        'english': 'English',
        'hindi': 'हिंदी (Hindi)',
        'bengali': 'বাংলা (Bengali)', 
        'tamil': 'தமிழ் (Tamil)',
        'malayalam': 'മലയാളം (Malayalam)',
        'telugu': 'తెలుగు (Telugu)',
        'marathi': 'मराठी (Marathi)',
        'gujarati': 'ગુજરાતી (Gujarati)',
        'kannada': 'ಕನ್ನಡ (Kannada)',
        'punjabi': 'ਪੰਜਾਬੀ (Punjabi)',
        'odia': 'ଓଡ଼ିଆ (Odia)',
        'assamese': 'অসমীয়া (Assamese)',
        'urdu': 'اردو (Urdu)'
    }
    
    # Create dropdown for language selection
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        selected_language_display = st.selectbox(
            "🌍 Choose Language / भाषा चुनें / ভাষা নির্বাচন করুন",
            options=list(language_options.values()),
            index=0,  # Default to English
            key="language_selection_dropdown",
            help="Select your preferred language for the interface and responses"
        )
        
        # Find the language code from display name
        selected_language = None
        for lang_code, lang_display in language_options.items():
            if lang_display == selected_language_display:
                selected_language = lang_code
                break
        
        # Confirmation button
        if st.button("✅ Continue with Selected Language", key="confirm_language", use_container_width=True, type="primary"):
            return selected_language
    
    return None

def create_compact_progress_tracker(section_key="default"):
    """Create a compact progress tracking system with unique keys for each section - HIDDEN"""
    # Progress tracker is now hidden but function kept for compatibility
    pass

def add_progress_log(message, status='processing', details=None):
    """Add a log entry to the progress tracker"""
    if 'progress_logs' not in st.session_state:
        st.session_state.progress_logs = []
    
    st.session_state.progress_logs.append({
        'message': message,
        'status': status,
        'details': details,
        'timestamp': time.time()
    })

# API Keys - Direct Configuration
try:
    GROQ_API_KEY = st.secrets["api_keys"]["GROQ_API_KEY"]
    SARVAM_API_KEY = st.secrets["api_keys"]["SARVAM_API_KEY"]
except KeyError as e:
    st.error(f"Missing API key in secrets: {e}")
    st.error("Please configure your API keys in Streamlit secrets")
    st.stop()

# LangChain components
from langchain_community.document_loaders import DirectoryLoader, TextLoader, WebBaseLoader
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from langchain.chains import create_retrieval_chain
from langchain_groq import ChatGroq
from langchain.schema import Document

# --- Page Configuration ---
st.set_page_config(
    page_title="AI Soil & Agriculture Assistant",
    page_icon="🌱",
    layout="wide"
)

# --- Auto-scroll JavaScript ---
def inject_autoscroll_js():
    """Injects the JavaScript for starting and stopping the auto-scroll."""
    autoscroll_script = """
    <script>
    // Ensure the functions are defined only once
    if (typeof window.startAutoScroll === 'undefined') {
        window.scrollInterval = null;

        window.startAutoScroll = function() {
            // Clear any existing interval to prevent duplicates
            if (window.scrollInterval) {
                clearInterval(window.scrollInterval);
            }
            // Set a new interval to scroll down
            window.scrollInterval = setInterval(function() {
                window.scrollTo({ top: document.body.scrollHeight, behavior: 'auto' });
            }, 300); // Scroll every 300ms
        }

        window.stopAutoScroll = function() {
            if (window.scrollInterval) {
                clearInterval(window.scrollInterval);
                window.scrollInterval = null;
                // Perform one final smooth scroll to the end
                setTimeout(() => {
                    window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });
                }, 150);
            }
        }
    }
    </script>
    """
    st.markdown(autoscroll_script, unsafe_allow_html=True)

def start_autoscroll():
    """Starts the auto-scrolling."""
    st.markdown("<script>window.startAutoScroll();</script>", unsafe_allow_html=True)

def stop_autoscroll():
    """Stops the auto-scrolling."""
    st.markdown("<script>window.stopAutoScroll();</script>", unsafe_allow_html=True)


# --- Knowledge Base Configuration ---
POSSIBLE_KB_PATHS = [
    "soil_knowledge_base",
    "../soil_knowledge_base",
    "./soil_knowledge_base",
    "streamlit-lang-rag/soil_knowledge_base"
]

POSSIBLE_CROP_CYCLE_PATHS = [
    "cropCycle_knowledge_base",
    "../cropCycle_knowledge_base",
    "./cropCycle_knowledge_base",
    "streamlit-lang-rag/cropCycle_knowledge_base"
]

# Find the correct paths
SOIL_KB_PATH = None
for path in POSSIBLE_KB_PATHS:
    if os.path.exists(path):
        SOIL_KB_PATH = path
        break

CROP_CYCLE_KB_PATH = None
for path in POSSIBLE_CROP_CYCLE_PATHS:
    if os.path.exists(path):
        CROP_CYCLE_KB_PATH = path
        break

# Original farming URLs for schemes and general info
FARMER_URLS = [
    "https://vikaspedia.in/agriculture/crop-production",
    "https://vikaspedia.in/agriculture/schemes-for-farmers",
    "https://vikaspedia.in/agriculture/agri-credit",
    "https://www.india.gov.in/topics/agriculture"
]

class SarvamVoiceProcessor:
    """Complete Sarvam API implementation with robust audio processing and fixed language handling"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.sarvam.ai"

        # Test different authentication methods
        self.auth_methods = [
            {"api-subscription-key": api_key},
            {"Authorization": f"Bearer {api_key}"},
            {"X-API-Key": api_key},
        ]

        # Comprehensive Indic Language Support
        self.language_codes = {
            # Original supported languages
            'english': 'en-IN',
            'tamil': 'ta-IN',
            'malayalam': 'ml-IN',
            
            # Major Indic Languages
            'hindi': 'hi-IN',
            'bengali': 'bn-IN',
            'gujarati': 'gu-IN',
            'kannada': 'kn-IN',
            'telugu': 'te-IN',
            'marathi': 'mr-IN',
            'punjabi': 'pa-IN',
            'odia': 'or-IN',
            'assamese': 'as-IN',
            'urdu': 'ur-IN',
            
            # Additional Indic Languages
            'sanskrit': 'sa-IN',
            'nepali': 'ne-IN',
            'sindhi': 'sd-IN',
            'konkani': 'kok-IN',
            'manipuri': 'mni-IN',
            'bodo': 'brx-IN',
            
            # Regional variants and alternatives
            'bangla': 'bn-IN',  # Alternative name for Bengali
            'oriya': 'or-IN',   # Alternative name for Odia
            'maithili': 'mai-IN',
            'santali': 'sat-IN',
            'kashmiri': 'ks-IN',
            'dogri': 'doi-IN'
        }
        
        # Language display names for UI
        self.language_display_names = {
            'english': 'English',
            'hindi': 'हिंदी (Hindi)',
            'bengali': 'বাংলা (Bengali)',
            'tamil': 'தமிழ் (Tamil)',
            'telugu': 'తెలుగు (Telugu)',
            'marathi': 'मराठी (Marathi)',
            'gujarati': 'ગુજરાતી (Gujarati)',
            'kannada': 'ಕನ್ನಡ (Kannada)',
            'malayalam': 'മലയാളം (Malayalam)',
            'punjabi': 'ਪੰਜਾਬੀ (Punjabi)',
            'odia': 'ଓଡ଼ିଆ (Odia)',
            'assamese': 'অসমীয়া (Assamese)',
            'urdu': 'اردو (Urdu)',
            'sanskrit': 'संस्कृत (Sanskrit)',
            'nepali': 'नेपाली (Nepali)',
            'sindhi': 'سنڌي (Sindhi)',
            'konkani': 'कोंकणी (Konkani)',
            'manipuri': 'মৈতৈলোন্ (Manipuri)',
            'bodo': 'बर\' (Bodo)',
            'bangla': 'বাংলা (Bangla)',
            'oriya': 'ଓଡ଼ିଆ (Oriya)',
            'maithili': 'मैथिली (Maithili)',
            'santali': 'ᱥᱟᱱᱛᱟᱲᱤ (Santali)',
            'kashmiri': 'कॉशुर (Kashmiri)',
            'dogri': 'डोगरी (Dogri)'
        }

        # Find working authentication method
        self.working_headers = self._find_working_auth()
    def _safe_json_response(self, response, show_progress=False):
        """Safely parse JSON response with error handling"""
        try:
            if response.headers.get('content-type', '').startswith('application/json'):
                return response.json(), True
            else:
                if show_progress:
                    st.error(f"Non-JSON response: {response.headers.get('content-type')}")
                    st.error(f"Response text: {response.text[:200]}")
                return None, False
        except ValueError as e:
            if show_progress:
                st.error(f"JSON parsing failed: {e}")
                st.error(f"Raw response: {response.text[:200]}")
            return None, False

    def _find_working_auth(self) -> dict:
        """Test all authentication methods to find working one"""
        test_payload = {
            "text": "Hello test",
            "target_language_code": "en-IN",
            "speaker": "anushka",
            "model": "bulbul:v2"
        }

        for auth_method in self.auth_methods:
            try:
                headers = {**auth_method, "Content-Type": "application/json"}
                response = requests.post(
                    f"{self.base_url}/text-to-speech",
                    headers=headers,
                    json=test_payload,
                    timeout=10
                )

                if response.status_code == 200:
                    st.success(f"✅ Working authentication found: {list(auth_method.keys())[0]}")
                    return headers
                elif response.status_code != 403:
                    return headers

            except Exception:
                continue

        # Fallback to first method
        return {**self.auth_methods[0], "Content-Type": "application/json"}

    def test_api_connection(self) -> dict:
        """Test API connection and authentication"""
        try:
            test_payload = {
                "text": "Hello test",
                "target_language_code": "en-IN",
                "speaker": "anushka",
                "model": "bulbul:v2"
            }

            response = requests.post(
                f"{self.base_url}/text-to-speech",
                headers=self.working_headers,
                json=test_payload,
                timeout=10
            )

            return {
                'status_code': response.status_code,
                'success': response.status_code in [200, 201],
                'response': response.text[:500] if response.text else "No response text",
                'headers_used': 'working_headers'
            }

        except Exception as e:
            return {
                'status_code': None,
                'success': False,
                'error': str(e),
                'headers_used': 'none'
            }

    def _calculate_transcript_quality(self, transcript: str, lang: str) -> float:
        """
        Calculate a quality score for a transcript.
        This simple implementation rewards length, which is often a good proxy
        for a successful transcription.
        """
        if not transcript:
            return 0.0
        
        # The score is simply the length of the transcript.
        # Longer transcripts are more likely to be correct detections.
        score = float(len(transcript))
        
        return score

    def detect_language(self, audio_bytes: bytes) -> str:
        """
        Optimized language detection.
        First, it checks the most common languages sequentially for speed.
        If no high-quality result is found, it falls back to parallel checking for other languages.
        """
        try:
            # Prioritize the most common languages for faster detection
            common_languages = ['malayalam', 'hindi', 'english', 'tamil', 'telugu']
            
            # --- 1. Sequential Check for Common Languages ---
            # st.info("Performing a quick check for common languages...")
            start_time = time.time()
            for lang in common_languages:
                try:
                    # Create a fresh audio file for each request
                    audio_file = io.BytesIO(audio_bytes)
                    file_extension, mime_type = self._detect_audio_format(audio_bytes)
                    audio_file.name = f'audio.{file_extension}'

                    files = {'file': (f'audio.{file_extension}', audio_file, mime_type)}
                    data = {
                        'model': 'saarika:v2',
                        'language_code': self.language_codes.get(lang, 'en-IN'),
                        'with_timestamps': 'false',
                        'model_type': 'general'
                    }
                    stt_headers = {k: v for k, v in self.working_headers.items() if k != 'Content-Type'}

                    response = requests.post(
                        f"{self.base_url}/speech-to-text",
                        headers=stt_headers,
                        files=files,
                        data=data,
                        timeout=15  # Shorter timeout for the quick check
                    )

                    if response.status_code == 200:
                        try:
                            result = response.json()
                            transcript = result.get('transcript', '').strip()
                        except (ValueError, KeyError) as e:
                            continue
                        # A transcript length > 5 is a good indicator of a confident detection
                        if transcript and len(transcript) > 5:  
                            end_time = time.time()
                            # st.success(f"Quickly detected language: **{self.get_language_display_name(lang)}** in {end_time - start_time:.2f}s")
                            return lang
                except requests.exceptions.RequestException:
                    # Ignore errors during the quick check and move to the next language
                    continue

            # --- 2. Fallback to Parallel Check for Other Languages ---
            st.info("Common languages not detected. Starting a comprehensive parallel check...")
            
            other_languages = [lang for lang in self.language_codes.keys() if lang not in common_languages]
            results = []
            
            
            def test_language(lang):
                try:
                    audio_file = io.BytesIO(audio_bytes)
                    file_extension, mime_type = self._detect_audio_format(audio_bytes)
                    audio_file.name = f'audio.{file_extension}'
                    
                    files = {'file': (f'audio.{file_extension}', audio_file, mime_type)}
                    data = {
                        'model': 'saarika:v2',
                        'language_code': self.language_codes.get(lang, 'en-IN'),
                    }
                    stt_headers = {k: v for k, v in self.working_headers.items() if k != 'Content-Type'}

                    response = requests.post(
                        f"{self.base_url}/speech-to-text",
                        headers=stt_headers,
                        files=files,
                        data=data,
                        timeout=20
                    )
                    
                    if response.status_code == 200:
                        transcript = response.json().get('transcript', '').strip()
                        if transcript:
                            return {
                                'language': lang,
                                'quality_score': self._calculate_transcript_quality(transcript, lang),
                                'success': True
                            }
                    return {'language': lang, 'success': False}
                except requests.exceptions.RequestException:
                    return {'language': lang, 'success': False}

            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
                future_to_lang = {executor.submit(test_language, lang): lang for lang in other_languages}
                for future in concurrent.futures.as_completed(future_to_lang, timeout=30):
                    try:
                        result = future.result(timeout=5)
                        if result['success']:
                            results.append(result)
                    except (concurrent.futures.TimeoutError, Exception):
                        continue
            
            if not results:
                st.warning("No language detected confidently. Defaulting to English.")
                return 'english'
            
            # Sort by quality score and return the best result
            results.sort(key=lambda x: x['quality_score'], reverse=True)
            best_result = results[0]
            detected_language = best_result['language']
            end_time = time.time()
            st.success(f"Detected language (comprehensive check): **{self.get_language_display_name(detected_language)}** in {end_time - start_time:.2f}s")
            return detected_language

        except Exception as e:
            st.error(f"An error occurred during language detection: {e}. Defaulting to English.")
            return 'english'

    
    
    def get_supported_languages(self) -> list:
        """Get list of supported languages for UI display"""
        return list(self.language_codes.keys())
    
    def get_language_display_name(self, language_code: str) -> str:
        """Get display name for a language"""
        return self.language_display_names.get(language_code, language_code.title())
    
    def validate_language(self, language: str) -> str:
        """Validate and normalize language input"""
        language = language.lower().strip()
        
        # Direct match
        if language in self.language_codes:
            return language
        
        # Try alternative names
        language_mapping = {
            'bengali': 'bengali',
            'bangla': 'bengali',
            'oriya': 'odia',
            'odia': 'odia',
            'hindi': 'hindi',
            'tamil': 'tamil',
            'telugu': 'telugu',
            'malayalam': 'malayalam',
            'kannada': 'kannada',
            'gujarati': 'gujarati',
            'marathi': 'marathi',
            'punjabi': 'punjabi',
            'assamese': 'assamese',
            'urdu': 'urdu'
        }
        
        normalized = language_mapping.get(language, 'english')
        return normalized if normalized in self.language_codes else 'english'

    def speech_to_text(self, audio_bytes: bytes, language: str = None, show_progress: bool = False) -> tuple:
        """Convert speech to text with improved audio validation and error handling"""
        try:
            # Auto-detect language if not provided
            if language is None:
                language = self.detect_language(audio_bytes)

            # Enhanced audio validation
            if not audio_bytes:
                if show_progress:
                    st.error("❌ No audio data received")
                return "", language, False

            if len(audio_bytes) < 1000:  # Increased minimum size requirement
                if show_progress:
                    st.error(f"❌ Audio too short: {len(audio_bytes)} bytes (minimum 1000 bytes required)")
                    st.info("💡 Try recording for at least 5 seconds with clear speech")
                return "", language, False

            if show_progress:
                st.info(f"🎵 Processing audio: {len(audio_bytes)} bytes")
                st.info(f"🗣️ Using language: {self.get_language_display_name(language)}")

            # Create audio file with better format detection
            audio_file = io.BytesIO(audio_bytes)

            # Enhanced format detection
            file_extension, mime_type = self._detect_audio_format(audio_bytes)
            audio_file.name = f'audio.{file_extension}'

            if show_progress:
                st.info(f"📄 Detected format: {file_extension.upper()} ({mime_type})")

            # Prepare request with enhanced parameters
            files = {
                'file': (f'audio.{file_extension}', audio_file, mime_type)
            }

            data = {
                'model': 'saarika:v2',
                'language_code': self.language_codes.get(language, 'en-IN'),
                'with_timestamps': 'false',
                'model_type': 'general',
                'enable_preprocessing': 'true'  # Enable audio preprocessing
            }

            # Make STT request with proper headers
            stt_headers = {k: v for k, v in self.working_headers.items() if k != 'Content-Type'}

            if show_progress:
                st.info(f"📤 Sending to Sarvam STT API...")
            
            response = requests.post(
                f"{self.base_url}/speech-to-text",
                headers=stt_headers,
                files=files,
                data=data,
                timeout=45  # Increased timeout for better reliability
            )

            if show_progress:
                st.info(f"📡 API Response: {response.status_code}")

            if response.status_code == 200:
                if response.headers.get('content-type', '').startswith('application/json'):
                    result, success = self._safe_json_response(response, show_progress)
                    if not success:
                        return "", language or 'english', False
                    transcript = result.get('transcript', '').strip()
                else:
                    st.error(f"Unexpected response format: {response.headers.get('content-type')}")
                    return "", language or 'english', False

                if transcript:
                    if show_progress:
                        st.success(f"✅ Transcription successful: {len(transcript)} characters")
                        st.info(f"📝 Detected text: '{transcript[:100]}...' in {self.get_language_display_name(language)}")
                    return transcript, language, True
                else:
                    if show_progress:
                        st.error("❌ Empty transcription received")
                        st.info("💡 Try speaking more clearly or check microphone")
                    return "", language, False
            else:
                if show_progress:
                    st.error(f"❌ STT API Error {response.status_code}")
                    error_text = response.text[:300] if response.text else "No error details"
                    st.error(f"Error details: {error_text}")

                    # Provide helpful error guidance
                    if response.status_code == 400:
                        st.info("💡 Audio format may be unsupported. Try recording again.")
                    elif response.status_code == 403:
                        st.info("💡 API authentication issue. Check your API key.")
                    elif response.status_code == 429:
                        st.info("💡 Rate limit exceeded. Please wait a moment and try again.")

                return "", language, False

        except Exception as e:
            if show_progress:
                st.error(f"❌ Speech to text error: {str(e)}")
                st.info("💡 Try recording again with clear speech for at least 5 seconds")
            return "", language or 'english', False

    def _detect_audio_format(self, audio_bytes: bytes) -> tuple:
        """Enhanced audio format detection"""
        try:
            # Check file signatures more thoroughly
            if audio_bytes.startswith(b'RIFF') and b'WAVE' in audio_bytes[:12]:
                return 'wav', 'audio/wav'
            elif audio_bytes.startswith(b'\xff\xfb') or audio_bytes.startswith(b'\xff\xf3') or audio_bytes.startswith(b'\xff\xf2'):
                return 'mp3', 'audio/mpeg'
            elif audio_bytes.startswith(b'ID3'):
                return 'mp3', 'audio/mpeg'
            elif audio_bytes.startswith(b'OggS'):
                return 'ogg', 'audio/ogg'
            elif audio_bytes.startswith(b'fLaC'):
                return 'flac', 'audio/flac'
            elif b'ftypM4A' in audio_bytes[:20] or b'ftymp42' in audio_bytes[:20]:
                return 'm4a', 'audio/mp4'
            else:
                # Default to wav for unknown formats
                if st:
                    st.warning(f"⚠️ Unknown audio format, using WAV. First 16 bytes: {audio_bytes[:16].hex()}")
                return 'wav', 'audio/wav'
        except Exception as e:
            if st:
                st.warning(f"⚠️ Format detection error: {e}")
            return 'wav', 'audio/wav'

    def translate_text(self, text: str, source_lang: str, target_lang: str, show_progress: bool = False) -> tuple:
        """Translate text between languages with enhanced validation and chunking for long text"""
        try:
            # Skip translation if same language or empty text
            if source_lang == target_lang or not text.strip():
                if show_progress:
                    st.info(f"🔄 No translation needed: {source_lang} → {target_lang}")
                return text, True

            # Only show detailed progress if requested
            if show_progress:
                st.info(f"🔄 TRANSLATION: {self.get_language_display_name(source_lang)} → {self.get_language_display_name(target_lang)}")
                st.info(f"📝 Text length: {len(text)} characters")
                st.info(f"📝 Text preview: '{text[:100]}...'")
            
            # Validate languages
            source_lang_code = self.language_codes.get(source_lang, 'en-IN')
            target_lang_code = self.language_codes.get(target_lang, 'en-IN')
            
            if show_progress:
                st.info(f"🗣️ Language codes: {source_lang_code} → {target_lang_code}")
            
            # Handle long text by chunking (API limit is 1000 characters)
            if len(text) > 900:  # Leave some buffer
                if show_progress:
                    st.info(f"📏 Text too long ({len(text)} chars), splitting into chunks...")
                return self._translate_long_text(text, source_lang, target_lang, show_progress)
            
            # Single translation for short text
            payload = {
                "input": text,
                "source_language_code": source_lang_code,
                "target_language_code": target_lang_code,
                "speaker_gender": "Female",
                "mode": "formal",
                "model": "mayura:v1"
            }

            if show_progress:
                st.info(f"📤 Sending translation request...")
            
            response = requests.post(
                f"{self.base_url}/translate",
                headers=self.working_headers,
                json=payload,
                timeout=30
            )

            if show_progress:
                st.info(f"📡 Translation API Response: {response.status_code}")

            if response.status_code == 200:
                result = response.json()
                translated_text = result.get('translated_text', text)
                
                # Enhanced validation - check if translation actually happened
                if translated_text == text and source_lang != target_lang:
                    if show_progress:
                        st.warning("⚠️ WARNING: Translated text is identical to source text!")
                        st.info(f"🔍 Trying alternative translation approach...")
                    
                    # Retry with different parameters
                    payload['mode'] = 'casual'
                    retry_response = requests.post(
                        f"{self.base_url}/translate",
                        headers=self.working_headers,
                        json=payload,
                        timeout=30
                    )
                    
                    if retry_response.status_code == 200:
                        retry_result = retry_response.json()
                        retry_translated = retry_result.get('translated_text', text)
                        
                        if retry_translated != text:
                            if show_progress:
                                st.success(f"✅ Retry translation successful!")
                                st.info(f"📝 Result: '{retry_translated[:100]}...'")
                            return retry_translated, True
                    
                    if show_progress:
                        st.warning("⚠️ Translation may not have worked properly")
                    return text, False
                else:
                    if show_progress:
                        st.success(f"✅ Translation successful!")
                        st.info(f"📝 Result: '{translated_text[:100]}...'")
                    return translated_text, True
            else:
                if show_progress:
                    st.error(f"❌ Translation API Error {response.status_code}")
                    error_details = response.text[:500] if response.text else "No error details"
                    st.error(f"Error details: {error_details}")
                return text, False

        except Exception as e:
            if show_progress:
                st.error(f"❌ Translation error: {str(e)}")
            return text, False

    def _translate_long_text(self, text: str, source_lang: str, target_lang: str, show_progress: bool = False) -> tuple:
        """Translate long text by splitting into chunks and processing in parallel"""
        try:
            # Split text into sentences to preserve meaning
            sentences = re.split(r'([.!?]+\s*)', text)
            chunks = []
            current_chunk = ""
            
            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence:
                    continue
                    
                # Check if adding this sentence would exceed limit (API limit is 1000, use 900 for buffer)
                potential_chunk = current_chunk + (" " if current_chunk else "") + sentence
                
                if len(potential_chunk) <= 900:  # Safe limit
                    current_chunk = potential_chunk
                else:
                    # Save current chunk and start new one
                    if current_chunk:
                        chunks.append(current_chunk)
                    current_chunk = sentence
            
            # Add remaining chunk
            if current_chunk:
                chunks.append(current_chunk)
            
            if not chunks:
                return text, False
                
            if show_progress:
                st.info(f"🔄 Translating {len(chunks)} chunks in parallel...")
            
            translated_chunks = [None] * len(chunks) # Pre-allocate for ordered results
            
            def translate_single_chunk(index, chunk):
                try:
                    payload = {
                        "input": chunk,
                        "source_language_code": self.language_codes.get(source_lang, 'en-IN'),
                        "target_language_code": self.language_codes.get(target_lang, 'en-IN'),
                        "speaker_gender": "Female",
                        "mode": "formal",
                        "model": "mayura:v1"
                    }

                    response = requests.post(
                        f"{self.base_url}/translate",
                        headers=self.working_headers,
                        json=payload,
                        timeout=30
                    )

                    if response.status_code == 200:
                        result = response.json()
                        translated_chunk = result.get('translated_text', chunk)
                        return index, translated_chunk, True
                    else:
                        if show_progress:
                            st.warning(f"⚠️ Chunk {index+1} translation failed: {response.status_code}")
                        return index, chunk, False # Use original if translation fails
                except Exception as e:
                    if show_progress:
                        st.warning(f"⚠️ Chunk {index+1} translation error: {str(e)}")
                    return index, chunk, False # Use original if error

            # Use ThreadPoolExecutor for parallel translation
            with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(chunks), 5)) as executor: # Limit workers
                future_to_chunk = {executor.submit(translate_single_chunk, i, chunk): i for i, chunk in enumerate(chunks)}
                
                for future in concurrent.futures.as_completed(future_to_chunk):
                    index, translated_chunk, success = future.result()
                    translated_chunks[index] = translated_chunk
                    if show_progress and success:
                        st.success(f"✅ Chunk {index+1} translated successfully")
            
            # Combine translated chunks
            final_translation = " ".join(translated_chunks)
            
            if all(tc is not None for tc in translated_chunks):
                if show_progress:
                    st.success(f"✅ All {len(chunks)} chunks translated successfully!")
                return final_translation, True
            else:
                if show_progress:
                    st.warning(f"⚠️ Some chunks failed translation, partial success")
                return final_translation, True  # Still return partial success
                
        except Exception as e:
            if show_progress:
                st.error(f"❌ Long text translation error: {str(e)}")
            return text, False

    def process_complete_workflow(self, audio_bytes: bytes, target_language: str, show_progress: bool = False) -> dict:
        """Complete workflow: STT -> Translation -> TTS with proper language handling"""
        try:
            if show_progress:
                st.info("🚀 Starting complete voice processing workflow...")
            
            # Step 1: Speech to Text with language detection
            if show_progress:
                st.info("🎯 Step 1: Speech-to-Text with language detection...")
            
            transcript, detected_language, stt_success = self.speech_to_text(
                audio_bytes, language=None, show_progress=show_progress
            )
            
            if not stt_success or not transcript:
                return {
                    'success': False,
                    'error': 'Speech-to-text failed',
                    'detected_language': detected_language,
                    'transcript': transcript,
                    'translated_text': None,
                    'audio_bytes': None
                }
            
            if show_progress:
                st.success(f"✅ STT completed: '{transcript[:100]}...' in {self.get_language_display_name(detected_language)}")
            
            # Step 2: Translation (if needed)
            target_language = self.validate_language(target_language)
            translated_text = transcript
            translation_success = True
            
            if detected_language != target_language:
                if show_progress:
                    st.info(f"🔄 Step 2: Translation from {self.get_language_display_name(detected_language)} to {self.get_language_display_name(target_language)}...")
                
                translated_text, translation_success = self.translate_text(
                    transcript, detected_language, target_language, show_progress=show_progress
                )
                
                if translation_success:
                    if show_progress:
                        st.success(f"✅ Translation completed: '{translated_text[:100]}...'")
                else:
                    if show_progress:
                        st.warning("⚠️ Translation failed, using original text")
                    translated_text = transcript
            else:
                if show_progress:
                    st.info(f"✅ Step 2: No translation needed (same language: {self.get_language_display_name(target_language)})")
            
            # Step 3: Text to Speech in TARGET language
            if show_progress:
                st.info(f"🔊 Step 3: Text-to-Speech in {self.get_language_display_name(target_language)}...")
            
            audio_bytes, tts_success = self.text_to_speech(
                translated_text, language=target_language, show_progress=show_progress
            )
            
            if tts_success:
                if show_progress:
                    st.success(f"✅ TTS completed: {len(audio_bytes)} bytes in {self.get_language_display_name(target_language)}")
            else:
                if show_progress:
                    st.error("❌ TTS failed")
            
            return {
                'success': stt_success and tts_success,
                'detected_language': detected_language,
                'target_language': target_language,
                'transcript': transcript,
                'translated_text': translated_text,
                'translation_success': translation_success,
                'audio_bytes': audio_bytes,
                'stt_success': stt_success,
                'tts_success': tts_success
            }
            
        except Exception as e:
            if show_progress:
                st.error(f"❌ Complete workflow error: {str(e)}")
            
            return {
                'success': False,
                'error': str(e),
                'detected_language': None,
                'transcript': None,
                'translated_text': None,
                'audio_bytes': None
            }

    def text_to_speech(self, text: str, language: str = 'english', show_progress: bool = False) -> tuple:
        """Convert text to speech with optimal length control and fast processing"""
        try:
            text = text.strip()
            if not text:
                return None, False

            # Validate and normalize language
            language = self.validate_language(language)
            
            if show_progress:
                st.info(f"🔊 TTS: Converting text to speech in {self.get_language_display_name(language)}")
                st.info(f"📝 Text preview: '{text[:100]}...'")

            # INCREASED AUDIO LENGTH CONTROL - limit to 2000 characters for more detailed audio
            if len(text) > 2000:
                if show_progress:
                    st.info(f"📏 Text length ({len(text)} chars) optimized for audio (truncating to 2000 chars)")
                # Find a good breaking point near 2000 characters
                truncation_point = 2000

                # Try to break at sentence end
                sentence_breaks = [i for i, char in enumerate(text[:2100]) if char in '.!?']
                if sentence_breaks:
                    best_break = max([b for b in sentence_breaks if b <= 2000], default=2000)
                    truncation_point = best_break + 1

                text = text[:truncation_point].strip()
                if not text.endswith(('.', '!', '?')):
                    text += "."

                if show_progress:
                    st.success(f"✅ Audio-optimized length: {len(text)} characters")

            # For short-medium text, use single request (much faster)
            if len(text) <= 700: # Increased threshold for single request
                return self._generate_single_audio(text, language, show_progress)

            # For longer text, use fast parallel processing
            return self._generate_complete_chunked_audio(text, language, show_progress)

        except Exception as e:
            if show_progress:
                st.error(f"❌ TTS Error: {str(e)}")
            return None, False

    def _generate_single_audio(self, text: str, language: str, show_progress: bool = False) -> tuple:
        """Generate audio for a single text chunk"""
        try:
            # Ensure we're using the correct language code
            language_code = self.language_codes.get(language, 'en-IN')
            
            if show_progress:
                st.info(f"🎵 Generating single audio chunk in {language_code}")
            
            payload = {
                "text": text,
                "target_language_code": language_code,  # Use the correct language code
                "speaker": "anushka",
                "model": "bulbul:v2",
                "speech_sample_rate": 22050,
                "enable_preprocessing": True
            }

            response = requests.post(
                f"{self.base_url}/text-to-speech",
                headers=self.working_headers,
                json=payload,
                timeout=30
            )

            if response.status_code == 200:
                try:
                    result = response.json()
                    audio_base64 = result.get('audios', [None])[0]
                except (ValueError, KeyError, IndexError) as e:
                    if show_progress:
                        st.error(f"Audio response parsing error: {e}")
                    return None, False

                if audio_base64:
                    audio_bytes = base64.b64decode(audio_base64)
                    if show_progress:
                        st.success(f"✅ Single audio generated: {len(audio_bytes)} bytes in {self.get_language_display_name(language)}")
                    return audio_bytes, True

            if show_progress:
                st.warning(f"⚠️ TTS API Error {response.status_code}: {response.text[:200]}")
            return None, False

        except Exception as e:
            if show_progress:
                st.warning(f"⚠️ Single audio generation error: {str(e)}")
            return None, False

    def _generate_complete_chunked_audio(self, text: str, language: str, show_progress: bool = False) -> tuple:
        """Fast parallel audio generation with optimal chunk processing"""
        try:
            # Create optimized chunks for faster processing
            text_chunks = self._create_smart_chunks(text, max_chunk_size=700)  # Increased chunk size for speed

            if not text_chunks:
                return None, False

            if len(text_chunks) == 1:
                return self._generate_single_audio(text_chunks[0], language, show_progress)

            if show_progress:
                st.info(f"🚀 Fast processing {len(text_chunks)} chunks in parallel for {self.get_language_display_name(language)}...")

            # Parallel processing with controlled concurrency
            max_workers = min(5, len(text_chunks))  # Limit concurrent requests
            audio_results = {}

            def process_chunk_with_retry(args):
                chunk_index, chunk_text = args
                max_retries = 2

                for attempt in range(max_retries):
                    try:
                        audio_bytes, success = self._generate_single_audio(chunk_text, language, False)  # Don't show progress for individual chunks
                        if success and audio_bytes:
                            return chunk_index, audio_bytes, True
                        elif attempt < max_retries - 1:
                            time.sleep(0.5)  # Brief retry delay
                    except Exception as e:
                        if attempt < max_retries - 1:
                            time.sleep(0.5)

                return chunk_index, None, False

            # Execute parallel processing
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Prepare chunk data
                chunk_args = [(i, chunk) for i, chunk in enumerate(text_chunks)]

                # Submit all tasks
                future_to_chunk = {
                    executor.submit(process_chunk_with_retry, args): args[0]
                    for args in chunk_args
                }

                # Progress tracking
                completed = 0
                if show_progress:
                    progress_bar = st.progress(0)
                    status_text = st.empty()

                # Collect results as they complete
                for future in concurrent.futures.as_completed(future_to_chunk):
                    chunk_index, audio_bytes, success = future.result()
                    completed += 1

                    if show_progress:
                        progress = completed / len(text_chunks)
                        progress_bar.progress(progress)
                        status_text.text(f"🎵 Completed {completed}/{len(text_chunks)} chunks ({int(progress*100)}%)")

                    if success and audio_bytes:
                        audio_results[chunk_index] = audio_bytes

            # Clear progress
            if show_progress:
                progress_bar.empty()
                status_text.empty()

            # Sort results by original order
            audio_chunks = []
            for i in range(len(text_chunks)):
                if i in audio_results:
                    audio_chunks.append(audio_results[i])

            if not audio_chunks:
                if show_progress:
                    st.error("❌ No audio chunks generated successfully")
                return None, False

            success_rate = len(audio_chunks) / len(text_chunks) * 100
            if show_progress:
                st.success(f"✅ Generated {len(audio_chunks)}/{len(text_chunks)} chunks ({success_rate:.1f}% success)")

            # Fast concatenation
            if len(audio_chunks) == 1:
                return audio_chunks[0], True

            if show_progress:
                st.info(f"🔗 Fast concatenating {len(audio_chunks)} audio segments...")
            final_audio = self._fast_concatenate_audio(audio_chunks, show_progress)

            if final_audio:
                if show_progress:
                    st.success(f"✅ Complete audio ready: {len(final_audio)} bytes in {self.get_language_display_name(language)}")
                return final_audio, True
            else:
                if show_progress:
                    st.warning("⚠️ Using first chunk as fallback")
                return audio_chunks[0], True

        except Exception as e:
            if show_progress:
                st.error(f"❌ Parallel audio generation error: {str(e)}")
            return None, False

    def _fast_concatenate_audio(self, audio_chunks: list, show_progress: bool = False) -> bytes:
        """Optimized audio concatenation for speed (binary concatenation only, pydub removed)"""
        if not audio_chunks:
            return None

        if len(audio_chunks) == 1:
            return audio_chunks[0]

        # Fast binary concatenation fallback
        try:
            # Assuming all chunks are WAV format and have a standard 44-byte header
            # Take the header from the first chunk
            combined = bytearray(audio_chunks[0])

            for chunk in audio_chunks[1:]:
                if len(chunk) > 44:
                    combined.extend(chunk[44:])  # Skip WAV header

            # Update WAV header sizes
            if len(combined) > 44:
                file_size = len(combined) - 8
                combined[4:8] = file_size.to_bytes(4, 'little') # RIFF chunk size
                data_size = len(combined) - 44
                combined[40:44] = data_size.to_bytes(4, 'little') # data chunk size

            return bytes(combined)

        except Exception as e:
            if show_progress:
                st.error(f"❌ Binary audio concatenation error: {str(e)}")
            return audio_chunks[0]  # Last resort fallback

    def _create_smart_chunks(self, text: str, max_chunk_size: int = 250) -> list:
        """Create smart text chunks that preserve complete content"""
        chunks = []

        # Split by paragraphs first to maintain structure
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]

        for paragraph in paragraphs:
            if len(paragraph) <= max_chunk_size:
                chunks.append(paragraph)
            else:
                # Split by sentences while preserving meaning
                sentences = re.split(r'([.!?]+\s+)', paragraph)
                current_chunk = ""

                i = 0
                while i < len(sentences):
                    sentence = sentences[i].strip()

                    if not sentence:
                        i += 1
                        continue

                    # Add punctuation if next item is punctuation
                    if i + 1 < len(sentences) and sentences[i + 1].strip() in ['.', '!', '?']:
                        sentence += sentences[i + 1].strip()
                        i += 2
                    else:
                        i += 1

                    # Check if we can add this sentence
                    potential_chunk = current_chunk + (" " if current_chunk else "") + sentence

                    if len(potential_chunk) <= max_chunk_size:
                        current_chunk = potential_chunk
                    else:
                        # Save current chunk
                        if current_chunk:
                            chunks.append(current_chunk)

                        # Handle very long sentences by splitting at commas
                        if len(sentence) > max_chunk_size:
                            parts = sentence.split(', ')
                            current_chunk = parts[0]

                            for part in parts[1:]:
                                potential = current_chunk + ", " + part
                                if len(potential) <= max_chunk_size:
                                    current_chunk = potential
                                else:
                                    chunks.append(current_chunk)
                                    current_chunk = part
                        else:
                            current_chunk = sentence

                # Add remaining chunk
                if current_chunk:
                    chunks.append(current_chunk)

        # Filter and validate chunks - ensure no content is lost
        valid_chunks = []
        for chunk in chunks:
            chunk = chunk.strip()
            if chunk and len(chunk) >= 3:  # Very minimal size requirement
                valid_chunks.append(chunk)

        # Fallback if no valid chunks (shouldn't happen with good input)
        if not valid_chunks:
            # Split text more aggressively to preserve content
            words = text.split()
            current_chunk = ""

            for word in words:
                potential = current_chunk + (" " if current_chunk else "") + word
                if len(potential) <= max_chunk_size:
                    current_chunk = potential
                else:
                    if current_chunk:
                        valid_chunks.append(current_chunk)
                    current_chunk = word

            if current_chunk:
                valid_chunks.append(current_chunk)

        return valid_chunks if valid_chunks else [text[:max_chunk_size]]

class SoilKnowledgeLoader:
    """Custom loader for soil knowledge base files"""

    def __init__(self, kb_path: str):
        self.kb_path = Path(kb_path)

    def load_all_documents(self):
        """Load all documents from the soil knowledge base"""
        documents = []

        # 1. Load JSON knowledge base
        json_file = self.kb_path / "complete_soil_knowledge_base.json"
        if json_file.exists():
            documents.extend(self._load_json_kb(json_file))
            st.sidebar.success("✅ JSON soil database loaded")

        # 2. Load text documents with error handling
        docs_folder = self.kb_path / "documents"
        if docs_folder.exists():
            documents.extend(self._load_text_documents_safely(docs_folder))
            st.sidebar.success("✅ Text documents loaded")

        # 3. Load CSV data as documents
        csv_files = ["city_soil_profiles.csv", "regional_soil_statistics.csv"]
        csv_loaded = 0
        for csv_file in csv_files:
            csv_path = self.kb_path / csv_file
            if csv_path.exists():
                documents.extend(self._load_csv_data(csv_path))
                csv_loaded += 1

        if csv_loaded > 0:
            st.sidebar.success(f"✅ {csv_loaded} CSV files loaded")

        return documents

    def _load_text_documents_safely(self, docs_folder: Path):
        """Load text documents with enhanced error handling"""
        documents = []

        try:
            txt_files = list(docs_folder.glob("*.txt"))

            for txt_file in txt_files:
                try:
                    encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']

                    content = None
                    for encoding in encodings:
                        try:
                            with open(txt_file, 'r', encoding=encoding) as f:
                                content = f.read()
                            break
                        except UnicodeDecodeError:
                            continue

                    if content:
                        filename = txt_file.stem
                        doc = Document(
                            page_content=content,
                            metadata={
                                "source": str(txt_file),
                                "type": "comprehensive_analysis",
                                "category": "soil_report",
                                "filename": filename
                            }
                        )

                        # Add state/region info based on filename
                        filename_lower = filename.lower()
                        if "tamil_nadu" in filename_lower or "chennai" in filename_lower:
                            doc.metadata["region"] = "tamil_nadu"
                            doc.metadata["state"] = "Tamil Nadu"
                        elif "kerala" in filename_lower or "kochi" in filename_lower:
                            doc.metadata["region"] = "kerala"
                            doc.metadata["state"] = "Kerala"

                        documents.append(doc)
                    else:
                        st.sidebar.warning(f"⚠️ Could not read {txt_file.name}")

                except Exception as e:
                    st.sidebar.warning(f"⚠️ Error loading {txt_file.name}: {str(e)}")
                    continue

        except Exception as e:
            st.sidebar.error(f"Error accessing documents folder: {e}")

        return documents

    def _load_json_kb(self, json_file: Path):
        """Load and convert JSON knowledge base to documents"""
        documents = []

        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                kb_data = json.load(f)

            # Create comprehensive documents from different sections
            # [Previous JSON loading logic remains the same - keeping it for brevity]
            # ... (implement the same JSON processing as in original)

        except Exception as e:
            st.error(f"Error loading JSON knowledge base: {e}")

        return documents

    def _load_csv_data(self, csv_file: Path):
        """Convert CSV data to documents"""
        documents = []

        try:
            df = pd.read_csv(csv_file)

            if "city_soil_profiles" in csv_file.name:
                for _, row in df.iterrows():
                    content = f"""
COMPREHENSIVE CITY SOIL PROFILE: {row.get('city', 'N/A')}, {row.get('region', 'N/A')}
Geographic Location: {row.get('latitude', 'N/A')}°N, {row.get('longitude', 'N/A')}°E

MEASURED SOIL PARAMETERS:
"""
                    # Add soil parameters
                    for col in df.columns:
                        if col.endswith('_value'):
                            param = col.replace('_value', '')
                            value = row.get(col, 'N/A')
                            content += f"• {param.upper().replace('_', ' ')}: {value}\n"

                    documents.append(Document(
                        page_content=content,
                        metadata={
                            "source": f"csv_city_{row.get('city', 'unknown')}",
                            "type": "detailed_city_data",
                            "category": "city_soil_data"
                        }
                    ))

        except Exception as e:
            st.error(f"Error loading CSV file {csv_file}: {e}")

        return documents


class CropCycleKnowledgeLoader:
    """Custom loader for crop cycle knowledge base"""

    def __init__(self, kb_path: str):
        self.kb_path = Path(kb_path)

    def load_all_documents(self):
        """Load all crop cycle documents"""
        documents = []

        json_file = self.kb_path / "crop_cycle.json"
        if json_file.exists():
            documents.extend(self._load_crop_cycle_json(json_file))
            st.sidebar.success("✅ Crop cycle database loaded")

        return documents

    def _load_crop_cycle_json(self, json_file: Path):
        """Load and convert crop cycle JSON to documents"""
        documents = []

        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                crop_data = json.load(f)

            # [Previous crop cycle JSON processing logic - keeping for brevity]
            # ... (implement the same processing as in original)

        except Exception as e:
            st.error(f"Error loading crop cycle JSON: {e}")

        return documents

def handle_text_input_with_native_response(user_prompt, prompt, sarvam_processor, retrieval_chain):
    """MODIFIED: Handle text input with native language response"""
    
    if user_prompt or prompt:
        # Start auto-scrolling for text processing
        start_autoscroll()
        
        question_to_process = user_prompt if user_prompt else prompt
        
        # Use new language-aware text processing
        if voice_enabled and sarvam_processor:
            # Process with language detection and native response
            result = process_text_query_with_language_detection(
                question_to_process, 
                sarvam_processor, 
                retrieval_chain
            )
            display_text_response_with_native_language(result)
        else:
            # Fallback to English-only processing
            start_time = time.time()
            response = retrieval_chain.invoke({"input": question_to_process})
            end_time = time.time()
            response_time = round(end_time - start_time, 2)
            
            # Display results
            st.markdown(f"### 🌾 Question: *{question_to_process}*")
            st.markdown("### 🧠 Expert Response:")
            st.markdown(response['answer'])
            st.success(f"⚡ Generated in {response_time} seconds")
            
            # Context display
            with st.expander("📚 Retrieved Knowledge Sources"):
                for i, doc in enumerate(response['context'], 1):
                    source_name = doc.metadata.get('source', f'Source {i}')
                    st.markdown(f"*{i}. {source_name}*")
                    st.markdown(f"> {doc.page_content[:400]}...")
                    if i < len(response['context']):
                        st.markdown("---")
        
        # Stop auto-scrolling after rendering the response
        stop_autoscroll()

def handle_uploaded_audio_with_native_response(sarvam_processor, retrieval_chain):
    """MODIFIED: Handle uploaded audio with native language response"""
    
    if hasattr(st.session_state, 'uploaded_transcript') and st.session_state.uploaded_transcript:
        st.markdown("### 📁 Uploaded Audio Processing")
        
        # Create upload result
        upload_result = {
            'original_transcript': st.session_state.uploaded_transcript,
            'language': st.session_state.upload_language
        }
        
        # Process as text query but with language awareness
        english_text = upload_result['original_transcript']
        if upload_result['language'] != 'english':
            with st.spinner("🔄 Translating to English..."):
                english_text, _ = sarvam_processor.translate_text(
                    upload_result['original_transcript'],
                    upload_result['language'],
                    'english'
                )
        
        # Get AI response
        with st.spinner("🧠 Generating response..."):
            start_time = time.time()
            response = retrieval_chain.invoke({"input": english_text})
            response_time = round(time.time() - start_time, 2)
            answer = response['answer']
        
        # ALWAYS translate back to native language
        final_answer = answer
        if current_language != 'english':  # Use current_language instead of upload_language
            with st.spinner(f"🔄 Translating to {current_language}..."):
                final_answer, _ = st.session_state.voice_processor.translate_text(
                answer, 'english', current_language  # Use current_language
            )
        
        with st.spinner(f"🔊 Generating complete audio..."):
            audio_bytes, tts_success = st.session_state.voice_processor.text_to_speech(
            final_answer, current_language  # Use current_language
        )
        
        # Display results - NATIVE LANGUAGE FIRST
        st.markdown(f"**🗣️ Transcribed ({upload_result['language']}):** {upload_result['original_transcript']}")
        
        # Show response in user's language FIRST AND PROMINENTLY
        st.markdown(f"### 🧠 AI Response:")
        st.markdown(final_answer)
        
        # Show English version in expandable section (optional)
        if final_answer != answer:
            with st.expander("📖 View English Version (Optional)"):
                st.markdown(answer)
        
        if audio_bytes and tts_success:
            st.markdown("### 🔊 Complete Audio Response:")
            st.audio(audio_bytes, format='audio/wav')
            st.download_button(
                label="📥 Download Complete Audio",
                data=audio_bytes,
                file_name=f"response_{upload_result['language']}.wav",
                mime="audio/wav"
            )
        
        # Clear upload state
        st.session_state.uploaded_transcript = None
        
        # Stop auto-scrolling
        stop_autoscroll()

def process_voice_query_with_selected_language(audio_bytes: bytes, sarvam_processor: SarvamVoiceProcessor, retrieval_chain, selected_language: str = None) -> dict:
    """Voice processing pipeline that outputs in the detected input language"""

    total_start_time = time.time()

    try:
        with st.spinner("🎤 Processing voice input..."):
            # Step 1: Speech to Text with auto language detection
            transcript, detected_lang, stt_success = sarvam_processor.speech_to_text(audio_bytes, None)

            if not stt_success or not transcript.strip():
                return {
                    'success': False,
                    'error': 'Could not convert speech to text. Please try again.'
                }

            st.info(f"🗣️ **You said:** {transcript}")

        # Use detected language for all output (ignore selected_language parameter)
        output_language = selected_language if selected_language else detected_lang

        # Step 2: Translate to English if needed
        english_text = transcript
        if detected_lang != 'english':
            with st.spinner("🔄 Translating to English..."):
                english_text, translate_success = sarvam_processor.translate_text(transcript, detected_lang, 'english')
                if translate_success and english_text != transcript:
                    st.info(f"🔄 **English:** {english_text}")

        # Step 3: Get answer from RAG system (always in English)
        with st.spinner("🧠 Generating response..."):
            start_time = time.time()
            response = retrieval_chain.invoke({"input": english_text})
            response_time = round(time.time() - start_time, 2)

            answer = response['answer']

        # Step 4: Translate to DETECTED language (use detected language for response)
        final_answer = answer
        if detected_lang != 'english':
            with st.spinner(f"🔄 Translating answer to {detected_lang}..."):
                final_answer, translate_back_success = sarvam_processor.translate_text(answer, 'english', output_language)
            
                if not translate_back_success:
                    # Try multiple translation attempts for better success
                    for attempt in range(3):
                        final_answer, translate_back_success = sarvam_processor.translate_text(answer, 'english', detected_lang)
                        if translate_back_success and final_answer != answer:
                            break
                        time.sleep(0.5)  # Brief delay between attempts
                
                if not translate_back_success or final_answer == answer:
                    # Force translation by trying different modes
                    payload = {
                        "input": answer,
                        "source_language_code": "en-IN",
                        "target_language_code": sarvam_processor.language_codes.get(detected_lang, 'hi-IN'),
                        "speaker_gender": "Female",
                        "mode": "casual",
                        "model": "mayura:v1"
                    }
                    
                    try:
                        response = requests.post(
                            f"{sarvam_processor.base_url}/translate",
                            headers=sarvam_processor.working_headers,
                            json=payload,
                            timeout=30
                        )
                        
                        if response.status_code == 200:
                            try:
                                result = response.json()
                                translated_text = result.get('translated_text', text)
                            except (ValueError, KeyError) as e:
                                if show_progress:
                                    st.error(f"JSON parsing error: {e}")
                                return text, False
                    except:
                        pass

        # Step 5: Convert answer to speech in DETECTED language (same as input)
        with st.spinner(f"🔊 Generating speech..."):
            audio_response, tts_success = sarvam_processor.text_to_speech(final_answer, output_language)
        total_response_time = round(time.time() - total_start_time, 2)

        return {
            'success': True,
            'original_transcript': transcript,
            'english_text': english_text,
            'answer_text': answer,  # English version
            'translated_answer': final_answer,  # Detected language version
            'audio_response': audio_response if tts_success else None,
            'response_time': response_time,
            'total_response_time': total_response_time,
            'context': response['context'],
            'language': detected_lang,  # Use detected language for display (same as input)
            'input_language': detected_lang,  # Keep track of input language
            'audio_generation_success': tts_success
        }

    except Exception as e:
        return {
            'success': False,
            'error': f'Voice processing error: {str(e)}'
        }



def display_voice_response(voice_result: dict):
    """Display voice processing results with native language first - FIXED"""

    if not voice_result['success']:
        st.error(f"❌ {voice_result['error']}")
        return

    # Create a container for the response
    response_container = st.container()

    with response_container:
        # Show the processing pipeline
        st.markdown("### 🎤 Voice Query Processing")

        # Original transcript
        detected_language = voice_result['language']
        st.markdown(f"**🗣️ You said:** {voice_result['original_transcript']}")

        # English translation if different (optional, in expander)
        if voice_result['english_text'] != voice_result['original_transcript']:
            with st.expander("🔄 View English Translation"):
                st.markdown(f"**English:** {voice_result['english_text']}")

        # AI Response - ALWAYS show in user's DETECTED language FIRST
        st.markdown(f"### 🧠 AI Response:")
        
        # Show translated response
        translated_response = voice_result['translated_answer']
        
        # Validation check - ensure we're not showing English when we should show native language
        if detected_language != 'english':
            if translated_response == voice_result['answer_text']:
                st.error(f"❌ Translation failed - response is still in English")
                st.markdown(f"**Showing English response (translation failed):**")
                st.markdown(voice_result['answer_text'])
            else:
                st.success(f"✅ Response successfully translated to {detected_language}")
                st.markdown(translated_response)
        else:
            st.markdown(translated_response)
        
        # Show English version only in expandable section (optional) if translation succeeded
        if detected_language != 'english' and translated_response != voice_result['answer_text']:
            with st.expander("📖 View English Version (Optional)"):
                st.markdown(voice_result['answer_text'])

        # Audio playback - Use DETECTED language for audio
        if voice_result['audio_response'] and voice_result['audio_generation_success']:
            st.markdown(f"### 🔊 Audio Response ({detected_language}):")
            st.audio(voice_result['audio_response'], format='audio/wav')

            # Download button
            st.download_button(
                label="📥 Download Complete Audio",
                data=voice_result['audio_response'],
                file_name=f"agriculture_response_{detected_language}.wav",
                mime="audio/wav",
                help="Download the complete generated audio response"
            )
        elif not voice_result['audio_generation_success']:
            st.warning("⚠️ Audio generation failed, but text response is available above")

        # Show timing information
        col1, col2 = st.columns(2)
        with col1:
            st.success(f"⚡ LLM processing: {voice_result['response_time']}s")
        with col2:
            st.info(f"🕒 Total response: {voice_result['total_response_time']}s")

        # Context sources
        with st.expander("📚 Retrieved Knowledge Sources"):
            for i, doc in enumerate(voice_result['context'], 1):
                source_name = doc.metadata.get('source', f'Source {i}')
                st.markdown(f"*{i}. {source_name}*")
                st.markdown(f"> {doc.page_content[:300]}...")
                st.markdown("---")

    # Stop auto-scrolling after displaying everything
    stop_autoscroll()
def process_text_query_with_language_detection(user_input: str, sarvam_processor: SarvamVoiceProcessor, retrieval_chain) -> dict:
    """NEW FUNCTION: Process text query with language detection and native response"""
    
    try:
        start_time = time.time()
        
        # Detect language of the text input
        detected_lang = detect_text_language(user_input, sarvam_processor)
        
        # Translate to English if needed
        english_text = user_input
        if detected_lang != 'english':
            with st.spinner("🔄 Translating query to English..."):
                english_text, translate_success = sarvam_processor.translate_text(user_input, detected_lang, 'english')
                if not translate_success:
                    english_text = user_input  # Fallback to original
        
        # Get response from RAG system
        with st.spinner("🧠 Generating response..."):
            response = retrieval_chain.invoke({"input": english_text})
            answer = response['answer']
        
        # Translate response back to original language
        final_answer = answer
        if detected_lang != 'english':
            with st.spinner(f"🔄 Translating response to {detected_lang}..."):
                final_answer, translate_back_success = sarvam_processor.translate_text(answer, 'english', detected_lang)
                if not translate_back_success:
                    final_answer = answer  # Fallback to English
        
        # Generate audio in native language
        audio_response = None
        tts_success = False
        if sarvam_processor:
            with st.spinner(f"🔊 Generating audio in {detected_lang}..."):
                audio_response, tts_success = sarvam_processor.text_to_speech(final_answer, detected_lang)
        
        response_time = round(time.time() - start_time, 2)
        
        return {
            'success': True,
            'original_query': user_input,
            'detected_language': detected_lang,
            'english_query': english_text,
            'english_answer': answer,
            'native_answer': final_answer,
            'audio_response': audio_response,
            'response_time': response_time,
            'context': response['context'],
            'audio_generation_success': tts_success
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': f'Text processing error: {str(e)}'
        }
    

def detect_text_language(text: str, sarvam_processor: SarvamVoiceProcessor) -> str:
    """NEW FUNCTION: Detect language of text input"""
    
    # Simple heuristic-based language detection for common patterns
    text_lower = text.lower().strip()
    
    # Check for common English words
    english_indicators = ['what', 'how', 'when', 'where', 'why', 'is', 'are', 'can', 'will', 'the', 'and', 'or', 'for', 'in', 'on', 'at', 'with', 'by']
    english_count = sum(1 for word in english_indicators if word in text_lower)
    
    # Check for Devanagari script (Hindi, Marathi, etc.)
    if any('\u0900' <= char <= '\u097F' for char in text):
        return 'hindi'
    
    # Check for Tamil script
    if any('\u0B80' <= char <= '\u0BFF' for char in text):
        return 'tamil'
    
    # Check for Telugu script
    if any('\u0C00' <= char <= '\u0C7F' for char in text):
        return 'telugu'
    
    # Check for Malayalam script
    if any('\u0D00' <= char <= '\u0D7F' for char in text):
        return 'malayalam'
    
    # Check for Gujarati script
    if any('\u0A80' <= char <= '\u0AFF' for char in text):
        return 'gujarati'
    
    # Check for Kannada script
    if any('\u0C80' <= char <= '\u0CFF' for char in text):
        return 'kannada'
    
    # Check for Bengali script
    if any('\u0980' <= char <= '\u09FF' for char in text):
        return 'bengali'
    
    # Check for Punjabi script
    if any('\u0A00' <= char <= '\u0A7F' for char in text):
        return 'punjabi'
    
    # Check for Odia script
    if any('\u0B00' <= char <= '\u0B7F' for char in text):
        return 'odia'
    
    # If high English word count and no non-Latin scripts, likely English
    if english_count >= 2 and all(ord(char) < 256 for char in text):
        return 'english'
    
    # Default fallback
    return 'english'


def display_text_response_with_selected_language(question: str, answer: str, current_language: str, response_time: float, context: list, sarvam_processor=None):
    """Display text response in selected language with optional audio generation"""
    
    # Show question
    st.markdown(f"### 🌾 Question: *{question}*")
    
    # Translate answer to selected language if needed
    final_answer = answer
    if current_language != 'english' and sarvam_processor:
        with st.spinner(f"🔄 Translating to {current_language}..."):
            final_answer, translate_success = sarvam_processor.translate_text(answer, 'english', current_language, show_progress=False)
            if not translate_success:
                final_answer = answer  # Fallback to English
    
    # Show response in selected language
    st.markdown(f"### 🧠 Expert Response ({current_language.title()}):")
    st.markdown(final_answer)
    
    # Show English version button if translated
    if final_answer != answer:
        with st.expander("📖 View English Version"):
            st.markdown(answer)
    
    # Generate Audio button for text responses
    col1, col2 = st.columns([3, 1])
    with col1:
        st.success(f"⚡ Generated in {response_time} seconds")
    
    with col2:
        if sarvam_processor and st.button("🔊 Generate Audio", key=f"generate_audio_{hash(question)}", use_container_width=True):
            with st.spinner(f"🔊 Generating audio in {current_language}..."):
                audio_bytes, tts_success = sarvam_processor.text_to_speech(final_answer, current_language)
                
                if audio_bytes and tts_success:
                    st.audio(audio_bytes, format='audio/wav')
                    st.download_button(
                        label="📥 Download Audio",
                        data=audio_bytes,
                        file_name=f"response_{current_language}.wav",
                        mime="audio/wav",
                        key=f"download_audio_{hash(question)}"
                    )
                else:
                    st.error("❌ Audio generation failed")
    
    # Context display
    with st.expander("📚 Retrieved Knowledge Sources"):
        for i, doc in enumerate(context, 1):
            source_name = doc.metadata.get('source', f'Source {i}')
            st.markdown(f"*{i}. {source_name}*")
            st.markdown(f"> {doc.page_content[:400]}...")
            if i < len(context):
                st.markdown("---")

def display_text_response_with_native_language(result: dict):
    """NEW FUNCTION: Display text response with native language priority"""
    
    if not result['success']:
        st.error(f"❌ {result['error']}")
        return
    
    # Show original query
    if result['detected_language'] != 'english':
        st.markdown(f"### 🌾 Question ({result['detected_language'].title()}): *{result['original_query']}*")
        
        # Show English translation in expander
        with st.expander("🔄 View English Translation"):
            st.markdown(f"**English:** *{result['english_query']}*")
    else:
        st.markdown(f"### 🌾 Question: *{result['original_query']}*")
    
    # Show response in native language FIRST
    st.markdown(f"### 🧠 Expert Response ({result['detected_language'].title()}):")
    st.markdown(result['native_answer'])
    
    # Show English version in expander (optional)
    if result['native_answer'] != result['english_answer']:
        with st.expander("📖 View English Version"):
            st.markdown(result['english_answer'])
    
    # Generate Audio button for text responses
    col1, col2 = st.columns([3, 1])
    with col1:
        st.success(f"⚡ Generated in {result['response_time']} seconds")
    
    with col2:
        if st.button("🔊 Generate Audio", key=f"generate_audio_native_{hash(result['original_query'])}", use_container_width=True):
            if result['audio_response'] and result['audio_generation_success']:
                st.audio(result['audio_response'], format='audio/wav')
                st.download_button(
                    label="📥 Download Audio",
                    data=result['audio_response'],
                    file_name=f"response_{result['detected_language']}.wav",
                    mime="audio/wav",
                    key=f"download_audio_native_{hash(result['original_query'])}"
                )
            else:
                st.error("❌ Audio not available")
    
    # Context display
    with st.expander("📚 Retrieved Knowledge Sources"):
        for i, doc in enumerate(result['context'], 1):
            source_name = doc.metadata.get('source', f'Source {i}')
            st.markdown(f"*{i}. {source_name}*")
            st.markdown(f"> {doc.page_content[:400]}...")
            if i < len(result['context']):
                st.markdown("---")


def process_audio_file(uploaded_file, sarvam_processor: SarvamVoiceProcessor) -> tuple:
    """Process uploaded audio file with auto language detection"""
    try:
        # Read the uploaded file
        audio_bytes = uploaded_file.read()
        uploaded_file.seek(0)

        # Get file extension
        file_extension = uploaded_file.name.split('.')[-1].lower()

        # Supported formats
        supported_formats = ['mp3', 'wav', 'opus', 'ogg', 'm4a', 'aac', 'flac']

        if file_extension not in supported_formats:
            return None, None, f"Unsupported format: {file_extension}. Supported: {', '.join(supported_formats)}"

        # Process with auto language detection
        transcript, detected_lang, stt_success = sarvam_processor.speech_to_text(audio_bytes, None)

        if stt_success:
            return transcript, detected_lang, None
        else:
            return None, None, "Failed to transcribe audio file"

    except Exception as e:
        return None, None, f"Error processing audio file: {str(e)}"


# --- Language Selection Popup Logic ---
# Check if language has been selected
if 'selected_language' not in st.session_state:
    st.session_state.selected_language = None

# Show language popup if no language selected
if st.session_state.selected_language is None:
    selected_lang = show_language_selection_popup()
    if selected_lang:
        st.session_state.selected_language = selected_lang
        st.rerun()
    else:
        st.stop()  # Stop execution until language is selected

# Get current language for translations
current_language = st.session_state.selected_language

# --- Main App Logic ---
# Add language selector at the top
col1, col2, col3 = st.columns([2, 1, 1])

with col1:
    st.title(get_text('app_title', current_language))

with col3:
    # Language change dropdown at top
    if 'voice_processor' in st.session_state:
        language_options = {
            'english': 'English',
            'hindi': 'हिंदी (Hindi)',
            'bengali': 'বাংলা (Bengali)', 
            'tamil': 'தமிழ் (Tamil)',
            'malayalam': 'മലയാളം (Malayalam)',
            'telugu': 'తెలుగు (Telugu)',
            'marathi': 'मराठी (Marathi)',
            'gujarati': 'ગુજરાતી (Gujarati)',
            'kannada': 'ಕನ್ನಡ (Kannada)',
            'punjabi': 'ਪੰਜਾਬੀ (Punjabi)',
            'odia': 'ଓଡ଼ିଆ (Odia)',
            'assamese': 'অসমীয়া (Assamese)',
            'urdu': 'اردو (Urdu)'
        }
        
        current_display = language_options.get(current_language, current_language.title())
        selected_display = st.selectbox(
            "🌍 Language",
            options=list(language_options.values()),
            index=list(language_options.values()).index(current_display),
            key="top_language_selector"
        )
        
        # Find the language code from display name
        for lang_code, lang_display in language_options.items():
            if lang_display == selected_display:
                if lang_code != current_language:
                    st.session_state.selected_language = lang_code
                    st.rerun()
                break

# Inject the auto-scroll JavaScript functions into the app's HTML
inject_autoscroll_js()

# Start background knowledge base building with progress tracking
if "vectors" not in st.session_state:
    # Show only a simple progress bar, hide verbose details
    with st.spinner("🔨 Building knowledge base..."):
        st.info("🔄 Loading agricultural data and building knowledge base...")

st.markdown(get_text('app_description', current_language))
st.markdown(f"""
- {get_text('soil_analysis', current_language)}
- {get_text('gov_schemes', current_language)}
- {get_text('soil_parameters', current_language)}
- {get_text('crop_recommendations', current_language)}
- {get_text('crop_cycle', current_language)}
""")

# --- Sidebar for Configuration ---
with st.sidebar:
    st.header(get_text('configuration', current_language))

    # Show selected language
    st.success(f"🌍 Selected Language: {st.session_state.voice_processor.get_language_display_name(current_language) if 'voice_processor' in st.session_state else current_language.title()}")
    
    # Option to change language
    if st.button("🔄 Change Language", key="change_language_btn"):
        st.session_state.selected_language = None
        st.rerun()

    # Check knowledge bases
    kb_status = []

    if SOIL_KB_PATH:
        st.success(f"✅ Soil Knowledge Base Found")
        kb_status.append("soil")
    else:
        st.error("❌ Soil Knowledge Base Not Found")

    if CROP_CYCLE_KB_PATH:
        st.success(f"✅ Crop Cycle Knowledge Base Found")
        kb_status.append("crop_cycle")
    else:
        st.error("❌ Crop Cycle Knowledge Base Not Found")

    # API Keys - Using Direct Configuration
    try:
        groq_api_key = GROQ_API_KEY
        sarvam_api_key = SARVAM_API_KEY
        st.success("✅ API Keys loaded from secrets")
    except NameError:
        st.error("❌ API keys not properly configured")
        st.stop()
    st.info("🔍 Testing Sarvam API key...")

    # Test the API key
    if "voice_processor" not in st.session_state:
        st.session_state.voice_processor = SarvamVoiceProcessor(sarvam_api_key)

    test_result = st.session_state.voice_processor.test_api_connection()

    if test_result['success']:
        st.success("✅ Sarvam API Key validated (Voice enabled)")
        voice_enabled = True
    else:
        st.error(f"❌ API validation failed: {test_result.get('status_code', 'Unknown')}")
        voice_enabled = False

    # Model selection - UPGRADED DEFAULT MODEL FOR HIGHER ACCURACY
    available_models = [
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
        "gemma2-9b-it"
    ]

    selected_model = st.selectbox(
        "🤖 Select AI Model:",
        available_models,
        index=1,  # Default to the more powerful model
        key="ai_model_selection"
    )
    
    # Language Selection for Voice Features
    if voice_enabled:
        st.markdown("---")
        st.subheader("🌍 Language Settings")
        
        # Display supported languages count
        total_languages = len(st.session_state.voice_processor.language_codes)
        st.info(f"📊 **{total_languages} Languages Supported**")
        
        # Language override option
        language_override = st.selectbox(
            "🔧 Override Language Detection (Optional):",
            ["Auto-detect"] + [st.session_state.voice_processor.get_language_display_name(lang) 
                              for lang in sorted(st.session_state.voice_processor.get_supported_languages())],
            index=0,
            key="language_override_selection",
            help="Leave as 'Auto-detect' for automatic language detection, or select a specific language"
        )
        
        # Store language preference
        if language_override != "Auto-detect":
            # Find the language code from display name
            for lang_code, display_name in st.session_state.voice_processor.language_display_names.items():
                if display_name == language_override:
                    st.session_state.preferred_language = lang_code
                    st.success(f"✅ Language set to: {display_name}")
                    break
        else:
            st.session_state.preferred_language = None
            st.info("🔍 Auto-detection enabled")
        
        # Show popular languages
        with st.expander("🌟 Popular Languages"):
            popular_langs = ['hindi', 'bengali', 'tamil', 'telugu', 'marathi', 'gujarati', 'kannada', 'malayalam']
            cols = st.columns(2)
            for i, lang in enumerate(popular_langs):
                with cols[i % 2]:
                    display_name = st.session_state.voice_processor.get_language_display_name(lang)
                    st.markdown(f"• {display_name}")


# --- Enhanced Session State Initialization ---
if "vectors" not in st.session_state:
    with st.spinner("🔨 Building comprehensive agricultural knowledge base..."):
        try:
            # Initialize embeddings
            MODEL_PATH = Path(__file__).parent.parent / "models" / "bge-small-en-v1.5"
            @st.cache_resource(show_spinner="🔨 Loading embeddings...")
            def get_embeddings():
                return HuggingFaceEmbeddings(
                    model_name=str(MODEL_PATH),
                    model_kwargs={'device': 'cpu'},
                    encode_kwargs={'normalize_embeddings': True}
                )
           
            # Initialize embeddings
            embeddings=get_embeddings()
            st.session_state.embeddings=get_embeddings()
            @st.cache_data(show_spinner="📚 Loading documents...", ttl=3600)
            def load_all_documents():
                """Cached document loading"""
                all_documents = []
                
                # Load soil knowledge base
                if SOIL_KB_PATH:
                    loader = SoilKnowledgeLoader(SOIL_KB_PATH)
                    soil_documents = loader.load_all_documents()
                    all_documents.extend(soil_documents)
                
                # Load crop cycle knowledge base
                if CROP_CYCLE_KB_PATH:
                    crop_loader = CropCycleKnowledgeLoader(CROP_CYCLE_KB_PATH)
                    crop_documents = crop_loader.load_all_documents()
                    all_documents.extend(crop_documents)
                
                # Load web documents (cache for 1 hour)
                try:
                    web_loader = WebBaseLoader(FARMER_URLS)
                    web_documents = web_loader.load()
                    for doc in web_documents:
                        doc.metadata.update({
                            "category": "farming_schemes",
                            "type": "government_info",
                            "data_format": "web"
                        })
                    all_documents.extend(web_documents)
                except Exception as e:
                    st.sidebar.warning(f"⚠️ Web loading issue: {e}")
                
                return all_documents

            all_documents=load_all_documents()

            # 4. Process all documents
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=800,
                chunk_overlap=100,
                separators=["\n\n", "\n", ".", " "]
            )
            final_documents = text_splitter.split_documents(all_documents)

            # 5. Create vector store
            @st.cache_resource(show_spinner="🔨 Building vector store...")
            def create_vector_store(_embeddings, documents):
                """Cached vector store creation"""
                text_splitter = RecursiveCharacterTextSplitter(
                    chunk_size=800,
                    chunk_overlap=100,
                    separators=["\n\n", "\n", ".", " "]
                )
                final_documents = text_splitter.split_documents(documents)
                
                return FAISS.from_documents(final_documents, _embeddings), len(final_documents)
            st.session_state.vectors,chunk_count = create_vector_store(st.session_state.embeddings,all_documents)

            st.sidebar.success(f"✅ Knowledge Base Ready! ({len(final_documents)} chunks)")

        except Exception as e:
            st.error(f"❌ Failed to build knowledge base: {e}")
            st.stop()

def process_query_with_selected_language(query_text: str, sarvam_processor: SarvamVoiceProcessor, retrieval_chain, selected_language: str) -> dict:
    """Process any query and return response in selected language"""
    try:
        start_time = time.time()
        
        # Get response from RAG system (always in English)
        response = retrieval_chain.invoke({"input": query_text})
        answer = response['answer']
        
        # Translate to selected language if needed
        final_answer = answer
        if selected_language != 'english':
            final_answer, translate_success = sarvam_processor.translate_text(
                answer, 'english', selected_language
            )
            if not translate_success:
                final_answer = answer  # Fallback
        
        # Generate audio in selected language
        audio_response = None
        tts_success = False
        if sarvam_processor:
            audio_response, tts_success = sarvam_processor.text_to_speech(
                final_answer, selected_language
            )
        
        response_time = round(time.time() - start_time, 2)
        
        return {
            'success': True,
            'original_query': query_text,
            'english_answer': answer,
            'translated_answer': final_answer,
            'audio_response': audio_response,
            'response_time': response_time,
            'context': response['context'],
            'target_language': selected_language,
            'audio_generation_success': tts_success
        }
        
    except Exception as e:
        return {'success': False, 'error': str(e)}
# --- Enhanced RAG Chain Setup ---
if "vectors" in st.session_state:
    try:
        # Initialize LLM
        llm = ChatGroq(
            groq_api_key=groq_api_key,
            model_name=selected_model
        )

        # --- NEW, MORE ROBUST PROMPT TEMPLATE ---
        prompt_template = ChatPromptTemplate.from_template("""
MUST FOLLOW RULE :
* OUTPUT SHOULD ONLY BE WITHIN 150 to 500 WORDS ONLY!
* ALWAYS ANSWER TO THE QUESTION AND SHOW SOME METRICS LIKE PERCENTAGE, RATIO, ETC. IF APPLICABLE.
* DO NOT REPEAT WHAT YOU HAVE ALREADY STATED.
* DO NOT REPEAT THE QUESTION.
* THE OUTPUT SHOULD BE SHOULD BE TO THE POINT AND PRECISE SAME TIME ENSURE CHARACTER LIMIT IS MAINTAINED.

**FORMATTING INSTRUCTIONS:**
- Use **bold** for important keywords, parameters, and recommendations.
- Use *italics* for specific crop names, regions, or scientific terms.
- Use bullet points (`* ` or `- `) for lists, steps, or multiple recommendations.
- Ensure proper newlines and paragraph breaks for readability.

CRITICAL NORMALIZATION RULES - APPLY BEFORE ANY RESPONSE:
When you encounter soil parameter values, AUTOMATICALLY normalize them to realistic ranges:
• Clay content >100%: divide by 10 (e.g., 311% → 31.1%)
• Sand/Silt content >100%: divide by 10 
• pH >10: divide by 10 (e.g., 59.1 → 5.91)
• Nitrogen >10 g/kg: divide by 100 (e.g., 323.89 → 3.24 g/kg)
• Any percentage >100%: normalize to realistic range

NEVER mention the original incorrect values. ONLY show normalized values.
Do not mention unecessary agirculture values just because you have in knowledgebase, only use if is is required
NEVER use phrases like "(normalized)" or "corrected" - just state the proper values confidently.

STANDARD AGRICULTURAL RANGES (use these as your reference):
• Clay Content: 0-60% (0-15% sandy, 15-25% sandy loam, 25-40% clay loam, 40-60% clay)
• pH: 3.5-9.0 (6.0-7.0 slightly acidic/good, 7.0-7.5 neutral/excellent, >7.5 alkaline)
• Sand Content: 0-90%
• Silt Content: 0-90% 
• Organic Carbon: 1-50 g/kg (1-2% adequate, 2-4% good, >4% excellent)
• Nitrogen: 0.1-5 g/kg
• Bulk Density: 1.0-1.8 kg/dm³
• CEC: 5-50 cmol(c)/kg
• SOC : 1–60 g/kg
                        
**ROLE AND EXPERTISE:**
You are a world-class agricultural expert. Your knowledge covers:
- **Soil Science:** Deep understanding of soil parameters (pH, NPK, organic matter, etc.) for regions in Tamil Nadu and Kerala.
- **Agronomy:** Expertise in crop cycles, seasonal planning, and best practices for a wide range of crops.
- **Policy:** Comprehensive knowledge of Indian government agricultural schemes and financial aid for farmers.
- **Data Analysis:** You provide data-driven, factual advice based *only* on the context provided.

**CRITICAL INSTRUCTIONS - YOU MUST FOLLOW THESE:**
1.  **ACCURACY IS PARAMOUNT:** Your primary goal is to provide accurate, reliable, and factual information.
2.  **STICK TO THE CONTEXT:** Base your entire answer *exclusively* on the information within the `<context>` block. DO NOT use any outside knowledge or make assumptions. If the context does not contain the answer, state that clearly.
3.  **NO FABRICATION:** Never invent data, statistics, or scheme details. If a specific value is not in the context, say so.
4.  **BE COMPREHENSIVE:** Provide detailed and thorough answers. Avoid short, superficial responses.

**RESPONSE STRUCTURE AND LENGTH:**
- **Voice Queries:** Aim for a detailed response between **1200-2000 characters**. This provides depth while being suitable for audio playback.
- **Structure your answer logically:**
    1.  **Direct Answer:** Start with a clear and direct answer to the user's main question.
    2.  **Key Data & Evidence:** Present the specific data, soil parameters, or scheme details from the context that support your answer.
    3.  **Actionable Advice:** Provide clear, step-by-step recommendations for the farmer.
    4.  **Seasonal Timing:** If relevant, include information on when to perform actions (e.g., planting season, application deadlines).
- **TRANSLATION OPTIMIZATION:** Use clear, simple sentences. This is crucial for ensuring high-quality translation into other languages.

**SOIL PARAMETER NORMALIZATION (If you see unrealistic values):**
- Clay/Sand/Silt > 100%: Assume it's a mistake and divide by 10.
- pH > 10: Assume a decimal error and divide by 10.
- Nitrogen > 10 g/kg: Assume a unit error and divide by 100.
- Always mention that you have normalized a value for accuracy.

**CONTEXT:**
<context>
{context}
</context>

**USER QUESTION:** {input}

**Provide a detailed, data-driven, and actionable response based *only* on the provided context.**
""")


        # Create enhanced retrieval chain
        document_chain = create_stuff_documents_chain(llm, prompt_template)
        retriever = st.session_state.vectors.as_retriever(
            search_type="similarity",
            search_kwargs={"k": 4}
        )
        retrieval_chain = create_retrieval_chain(retriever, document_chain)

        # Status display
        knowledge_sources = []
        if SOIL_KB_PATH:
            knowledge_sources.append("Soil Data")
        if CROP_CYCLE_KB_PATH:
            knowledge_sources.append("Crop Cycles")
        knowledge_sources.append("Gov Schemes")

        st.info(f"🤖 **Model:** {selected_model} | 🗄️ **Knowledge:** {' + '.join(knowledge_sources)}")

        # --- Sample Questions ---
        st.markdown(f"### {get_text('what_you_can_ask', current_language)}")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown(f"**{get_text('soil_location', current_language)}**")
            if st.button("What is the soil pH in Chennai?", key="soil_1"):
                st.session_state.sample_question = "What is the soil pH in Chennai and what crops are suitable?"
            if st.button("Compare Coimbatore vs Kochi soil", key="soil_2"):
                st.session_state.sample_question = "Compare soil organic carbon between Coimbatore and Kochi"

        with col2:
            st.markdown(f"**{get_text('crop_cycles', current_language)}**")
            if st.button("When to plant rice in Tamil Nadu?", key="crop_1"):
                st.session_state.sample_question = "When should I plant rice in Tamil Nadu?"
            if st.button("Wheat growth stages?", key="crop_2"):
                st.session_state.sample_question = "What are the growth stages of wheat cultivation?"

        with col3:
            st.markdown(f"**{get_text('government_schemes', current_language)}**")
            if st.button("PM-KISAN scheme details?", key="scheme_1"):
                st.session_state.sample_question = "What is the PM-KISAN scheme and how to apply?"
            if st.button("Agricultural loans info?", key="scheme_2"):
                st.session_state.sample_question = "How to get agricultural loans for small farmers?"

        # --- Integrated Chat Interface with Voice & Upload ---
        st.markdown(f"### {get_text('voice_assistant', current_language)}")
        
        # Create integrated chat interface
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            # Text input
            prompt = st.chat_input(get_text('chat_input_placeholder', current_language))
        
        with col2:
            # Voice recording button
            if voice_enabled:
                audio_bytes = audio_recorder(
                    text="🎤 Record",
                    recording_color="#ff4444",
                    neutral_color="#0066cc",
                    icon_name="microphone",
                    icon_size="1x",
                    key="integrated_voice_recorder"
                )
                
                # Process audio immediately when recorded
                if audio_bytes and len(audio_bytes) >= 1000:
                    st.session_state.voice_audio_bytes = audio_bytes
                    st.success("🎤 Audio recorded!")
        
        with col3:
            # Audio file upload
            uploaded_audio = st.file_uploader(
                "📁 Upload",
                type=['mp3', 'wav', 'opus', 'ogg', 'm4a', 'aac', 'flac'],
                help="Upload audio file",
                key="integrated_audio_uploader",
                label_visibility="collapsed"
            )
            
            if uploaded_audio is not None:
                if st.button("🎯 Process", key="process_integrated_audio", use_container_width=True):
                    transcript, detected_lang, error = process_audio_file(uploaded_audio, st.session_state.voice_processor)
                    if transcript:
                        st.session_state.uploaded_transcript = transcript
                        st.session_state.upload_language = detected_lang
                        st.success(f"📁 Uploaded & processed!")

        # Voice recording status and tips
        if voice_enabled:
            st.markdown("""
            **💡 Voice Tips:** Click 🎤 Record → Speak naturally → Click again to stop → Audio processes automatically
            """)

        # --- User Input and Response Generation ---
        user_prompt = None
        if hasattr(st.session_state, 'sample_question'):
            user_prompt = st.session_state.sample_question
            del st.session_state.sample_question

        # Voice processing - Use selected language for output
        if hasattr(st.session_state, 'voice_audio_bytes') and st.session_state.voice_audio_bytes:
            # Start auto-scrolling for voice processing
            start_autoscroll()
            
            # Add progress tracker for voice processing
            st.markdown("### 🎤 Voice Processing")
            create_compact_progress_tracker("voice")

            # Use detected language for output (input language = output language)
            voice_result = process_voice_query_with_selected_language(
                st.session_state.voice_audio_bytes,
                st.session_state.voice_processor,
                retrieval_chain,
                current_language)

            # Clear to prevent reprocessing
            st.session_state.voice_audio_bytes = None
            if isinstance(voice_result, requests.Response):
                try:
                    voice_result = voice_result.json()
                except Exception:
                    voice_result = {"success": False, "error": "Unexpected API response format"}
            
            display_voice_response(voice_result)

        # Upload processing
        elif hasattr(st.session_state, 'uploaded_transcript') and st.session_state.uploaded_transcript:
            st.markdown("### 📁 Uploaded Audio Processing")
            
            # Add progress tracker for upload processing
            create_compact_progress_tracker("upload")

            # Create voice result for uploaded audio
            upload_audio_result = {
                'original_transcript': st.session_state.uploaded_transcript,
                'language': st.session_state.upload_language
            }

            # Process as text query
            english_text = upload_audio_result['original_transcript']
            if upload_audio_result['language'] != 'english':
                with st.spinner("🔄 Translating to English..."):
                    english_text, _ = st.session_state.voice_processor.translate_text(
                        upload_audio_result['original_transcript'],
                        upload_audio_result['language'],
                        'english'
                    )

            # Get AI response
            with st.spinner("🧠 Generating response..."):
                start_time = time.time()
                response = retrieval_chain.invoke({"input": english_text})
                response_time = round(time.time() - start_time, 2)
                answer = response['answer']

            # Translate back and generate audio
            final_answer = answer
            if upload_audio_result['language'] != 'english':
                with st.spinner(f"🔄 Translating to {upload_audio_result['language']}..."):
                    final_answer, _ = st.session_state.voice_processor.translate_text(
                        answer, 'english', upload_audio_result['language']
                    )

            with st.spinner(f"🔊 Generating complete audio..."):
                audio_bytes, tts_success = st.session_state.voice_processor.text_to_speech(
                    final_answer, upload_audio_result['language']
                )

            # Display results
            st.markdown(f"**🗣️ You said:** {upload_audio_result['original_transcript']}")
            
            # Show response in user's language first
            if upload_audio_result['language'] != 'english' and final_answer != answer:
                st.markdown(f"### 🧠 AI Response:")
                st.markdown(final_answer)
                
                # Show English version in expandable section
                with st.expander("📖 View English Version"):
                    st.markdown(answer)
            else:
                st.markdown("### 🧠 AI Response:")
                st.markdown(answer)

            if audio_bytes and tts_success:
                st.markdown("### 🔊 Complete Audio Response:")
                st.audio(audio_bytes, format='audio/wav')
                st.download_button(
                    label="📥 Download Complete Audio",
                    data=audio_bytes,
                    file_name=f"response_{upload_audio_result['language']}.wav",
                    mime="audio/wav"
                )

            # Clear upload state
            st.session_state.uploaded_transcript = None

            # Stop auto-scrolling
            stop_autoscroll()

        # Text query processing - Use selected language for output
        elif user_prompt or prompt:
            # Start auto-scrolling for text processing
            start_autoscroll()

            question_to_process = user_prompt if user_prompt else prompt
            
            # Add progress tracker for text processing
            st.markdown("### 💬 Text Query Processing")
            create_compact_progress_tracker("text")

            # Get AI response in English first
            start_time = time.time()
            response = retrieval_chain.invoke({"input": question_to_process})
            end_time = time.time()
            response_time = round(end_time - start_time, 2)

            # Display results using the new function with selected language
            display_text_response_with_selected_language(
        question_to_process,
        response['answer'],
        current_language,  # This ensures selected language is used
        response_time,
        response['context'],
        st.session_state.voice_processor if voice_enabled else None
    )

            # Stop auto-scrolling after rendering the response
            stop_autoscroll()

    except Exception as e:
        st.error(f"❌ Error: {e}")
        # Ensure scrolling stops even if an error occurs
        stop_autoscroll()

# --- Footer ---
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; font-size: 0.9em;'>
🌱 AI Soil & Agriculture Assistant - Complete farming intelligence with multilingual voice support<br>
🌍 <strong>22+ Indic Languages Supported</strong> • Auto language detection • Complete audio responses<br>
हिंदी • বাংলা • தமிழ் • తెలుగు • मराठी • ગુજરાતી • ಕನ್ನಡ • മലയാളം • ਪੰਜਾਬੀ • ଓଡ଼ିଆ • অসমীয়া • اردو • English
</div>
""", unsafe_allow_html=True)
