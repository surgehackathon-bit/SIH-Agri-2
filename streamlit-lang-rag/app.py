import streamlit as st
import os
import time
import json
import pandas as pd
from pathlib import Path

# Set USER_AGENT to avoid warnings
os.environ.setdefault('USER_AGENT', 'StreamlitAgricultureApp/1.0')

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

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

# --- Knowledge Base Configuration ---
# Check for soil knowledge base in current directory
POSSIBLE_KB_PATHS = [
    "soil_knowledge_base",
    "../soil_knowledge_base", 
    "./soil_knowledge_base",
    "streamlit-lang-rag/soil_knowledge_base"
]

# Check for crop cycle knowledge base in current directory
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
            # Get all .txt files in the directory
            txt_files = list(docs_folder.glob("*.txt"))
            
            for txt_file in txt_files:
                try:
                    # Try different encodings
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
                        # Create document
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
                        if "tamil_nadu" in filename_lower or "chennai" in filename_lower or "coimbatore" in filename_lower:
                            doc.metadata["region"] = "tamil_nadu"
                            doc.metadata["state"] = "Tamil Nadu"
                        elif "kerala" in filename_lower or "kochi" in filename_lower or "alappuzha" in filename_lower:
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
            
            # Create documents from different sections
            # 1. Metadata document
            metadata_content = f"""
SOIL KNOWLEDGE BASE OVERVIEW
============================
Data Source: {kb_data.get('metadata', {}).get('data_source', 'SoilGrids 2.0')}
Created: {kb_data.get('metadata', {}).get('created_date', 'N/A')}
Coverage Area: {kb_data.get('metadata', {}).get('coverage_area', 'Tamil Nadu and Kerala, India')}
Total Parameters: {kb_data.get('metadata', {}).get('total_parameters', 10)} soil parameters analyzed
Resolution: {kb_data.get('metadata', {}).get('resolution', '250m global grid')}
Coordinate System: {kb_data.get('metadata', {}).get('coordinate_system', 'EPSG:4326')}

This knowledge base contains comprehensive soil analysis for Tamil Nadu and Kerala states in India, 
covering major cities and agricultural regions with detailed soil parameter measurements.
"""
            documents.append(Document(
                page_content=metadata_content,
                metadata={"source": "soil_metadata", "type": "overview", "category": "soil_data"}
            ))
            
            # 2. Parameter definitions
            param_defs = kb_data.get('parameter_definitions', {})
            for param_key, param_info in param_defs.items():
                content = f"""
SOIL PARAMETER GUIDE: {param_info.get('name', param_key).upper()}
{'='*60}
Parameter Code: {param_key}
Full Name: {param_info.get('name', 'N/A')}
Description: {param_info.get('description', 'N/A')}
Measurement Unit: {param_info.get('unit', 'N/A')}
Agricultural Importance: {param_info.get('importance', 'N/A')}

This parameter is critical for understanding soil health and agricultural potential in farming systems.
"""
                documents.append(Document(
                    page_content=content,
                    metadata={
                        "source": f"parameter_{param_key}", 
                        "type": "parameter_definition", 
                        "category": "soil_science",
                        "parameter": param_key
                    }
                ))
            
            # 3. Regional data summaries
            regions = kb_data.get('regions', {})
            for region_key, region_data in regions.items():
                region_name = region_data.get('region_info', {}).get('name', region_key.replace('_', ' ').title())
                
                # Regional overview
                region_content = f"""
REGIONAL SOIL ANALYSIS: {region_name.upper()}
{'='*70}
State: {region_name}
Cities Analyzed: {len(region_data.get('city_profiles', {}))} major urban areas
Agricultural Regions Covered: Multiple districts and farming zones

COMPREHENSIVE SOIL CHARACTERISTICS:
"""
                # Add soil parameters summary
                soil_params = region_data.get('soil_parameters', {})
                for param, param_data in soil_params.items():
                    if '0-5cm' in param_data and 'statistics' in param_data['0-5cm']:
                        stats = param_data['0-5cm']['statistics']
                        param_name = param_defs.get(param, {}).get('name', param.upper())
                        unit = param_defs.get(param, {}).get('unit', '')
                        
                        region_content += f"""
• {param_name}: Regional average {stats.get('mean', 0):.2f} {unit}
  Value range: {stats.get('min', 0):.2f} to {stats.get('max', 0):.2f} {unit}
  Agricultural interpretation: {param_data['0-5cm'].get('interpretation', 'Standard levels for the region')}
"""
                
                # Add agricultural context
                region_content += f"""

AGRICULTURAL CONTEXT FOR {region_name.upper()}:
This region's soil conditions are suitable for various crops based on the measured parameters.
The soil analysis helps farmers make informed decisions about crop selection, fertilization,
and soil management practices specific to {region_name}.
"""
                
                documents.append(Document(
                    page_content=region_content,
                    metadata={
                        "source": f"region_{region_key}", 
                        "type": "regional_analysis", 
                        "category": "regional_soil",
                        "region": region_key,
                        "state": region_name
                    }
                ))
                
                # City profiles
                city_profiles = region_data.get('city_profiles', {})
                for city_name, city_data in city_profiles.items():
                    city_content = f"""
CITY AGRICULTURAL PROFILE: {city_name.upper()}, {region_name.upper()}
{'='*80}
Location: {city_data.get('city_info', {}).get('lat', 'N/A')}°N, {city_data.get('city_info', {}).get('lon', 'N/A')}°E
Analysis Area: {city_data.get('buffer_km', 10)} km radius around city center
Agricultural Zone: Urban and peri-urban farming areas

DETAILED SOIL ANALYSIS:
"""
                    soil_data = city_data.get('soil_data', {})
                    for param, data in soil_data.items():
                        param_name = param_defs.get(param, {}).get('name', param.upper())
                        city_content += f"""
• {param_name}: {data.get('mean', 'N/A')} {data.get('unit', '')}
  Agricultural significance: {data.get('interpretation', 'Standard measurement for agricultural planning')}
"""
                    
                    # Add agricultural suitability
                    suitability = city_data.get('agricultural_suitability', {})
                    if suitability:
                        city_content += f"""

CROP SUITABILITY ASSESSMENT FOR {city_name.upper()}:
"""
                        for category, crops in suitability.items():
                            if crops and isinstance(crops, list):
                                category_name = category.replace('_', ' ').title()
                                city_content += f"{category_name}: {', '.join(crops)}\n"
                    
                    # Add management recommendations
                    recommendations = city_data.get('management_recommendations', [])
                    if recommendations:
                        city_content += f"""

SOIL MANAGEMENT RECOMMENDATIONS FOR {city_name.upper()}:
"""
                        for i, rec in enumerate(recommendations, 1):
                            city_content += f"{i}. {rec}\n"
                    
                    # Add farming context
                    city_content += f"""

FARMING OPPORTUNITIES IN {city_name.upper()}:
Based on the soil analysis, farmers in and around {city_name} can optimize their 
agricultural practices by understanding these specific soil conditions. This data
supports precision farming, crop selection, and sustainable agricultural development.
"""
                    
                    documents.append(Document(
                        page_content=city_content,
                        metadata={
                            "source": f"city_{city_name.lower().replace(' ', '_')}",
                            "type": "city_profile",
                            "category": "city_agriculture",
                            "region": region_key,
                            "state": region_name,
                            "city": city_name
                        }
                    ))
            
        except Exception as e:
            st.error(f"Error loading JSON knowledge base: {e}")
        
        return documents
    
    def _load_csv_data(self, csv_file: Path):
        """Convert CSV data to documents"""
        documents = []
        
        try:
            df = pd.read_csv(csv_file)
            
            if "city_soil_profiles" in csv_file.name:
                # Create documents for each city
                for _, row in df.iterrows():
                    content = f"""
COMPREHENSIVE CITY SOIL PROFILE: {row.get('city', 'N/A')}, {row.get('region', 'N/A').replace('_', ' ').upper()}
{'='*80}
Geographic Location: {row.get('latitude', 'N/A')}°N, {row.get('longitude', 'N/A')}°E
Agricultural Assessment Area: {row.get('buffer_km', 'N/A')} km radius analysis

MEASURED SOIL PARAMETERS:
"""
                    # Add all soil parameters
                    for col in df.columns:
                        if col.endswith('_value'):
                            param = col.replace('_value', '')
                            unit_col = f"{param}_unit"
                            value = row.get(col, 'N/A')
                            unit = row.get(unit_col, '') if unit_col in df.columns else ''
                            content += f"• {param.upper().replace('_', ' ')}: {value} {unit}\n"
                    
                    # Add agricultural assessments
                    crops = row.get('highly_suitable_crops', '')
                    if crops and str(crops).strip() and str(crops) != 'nan':
                        content += f"\nHIGHLY SUITABLE CROPS: {crops}\n"
                    
                    limitations = row.get('soil_limitations', '')
                    if limitations and str(limitations).strip() and str(limitations) != 'nan':
                        content += f"\nSOIL LIMITATIONS: {limitations}\n"
                    
                    recommendations = row.get('management_recommendations', '')
                    if recommendations and str(recommendations).strip() and str(recommendations) != 'nan':
                        content += f"\nMANAGEMENT RECOMMENDATIONS: {recommendations}\n"
                    
                    content += f"""
AGRICULTURAL PLANNING NOTES:
This soil profile data is essential for farmers and agricultural planners in {row.get('city', 'this area')}
to make informed decisions about crop selection, soil management, and sustainable farming practices.
"""
                    
                    documents.append(Document(
                        page_content=content,
                        metadata={
                            "source": f"csv_city_{row.get('city', 'unknown').lower().replace(' ', '_')}",
                            "type": "detailed_city_data",
                            "category": "city_soil_data",
                            "city": row.get('city', 'Unknown'),
                            "region": row.get('region', 'Unknown'),
                            "data_format": "csv"
                        }
                    ))
            
            elif "regional_soil_statistics" in csv_file.name:
                # Create documents for regional statistics
                for _, row in df.iterrows():
                    param_name = row.get('parameter_name', 'Unknown Parameter')
                    region = row.get('region', 'Unknown Region')
                    
                    content = f"""
REGIONAL SOIL PARAMETER STATISTICS: {param_name.upper()} in {region.replace('_', ' ').upper()}
{'='*90}
Soil Parameter: {row.get('parameter', 'N/A')} ({param_name})
Measurement Unit: {row.get('unit', 'N/A')}
Region: {region.replace('_', ' ').title()}

STATISTICAL ANALYSIS:
• Regional Average: {row.get('mean', 'N/A')}
• Median Value: {row.get('median', 'N/A')}
• Value Range: {row.get('min', 'N/A')} to {row.get('max', 'N/A')}
• Standard Deviation: {row.get('std', 'N/A')}
• Data Points Analyzed: {row.get('count', 'N/A')} measurements
• 25th Percentile: {row.get('q25', 'N/A')}
• 75th Percentile: {row.get('q75', 'N/A')}

AGRICULTURAL SIGNIFICANCE:
This statistical analysis of {param_name.lower()} across {region.replace('_', ' ')} provides
farmers and agricultural researchers with reliable data for regional farming decisions.
The variation in values helps understand soil diversity and management needs across the region.
"""
                    documents.append(Document(
                        page_content=content,
                        metadata={
                            "source": f"csv_stats_{row.get('parameter', 'unknown')}_{region}",
                            "type": "statistical_analysis",
                            "category": "regional_statistics", 
                            "parameter": row.get('parameter', 'unknown'),
                            "region": region,
                            "data_format": "csv"
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
        
        # Load crop_cycle.json
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
            
            # Handle both list and dictionary formats
            if isinstance(crop_data, list):
                # Convert list to dictionary format
                crop_dict = {}
                for i, crop_item in enumerate(crop_data):
                    if isinstance(crop_item, dict):
                        # Use crop name if available, otherwise use index
                        crop_name = crop_item.get('name', crop_item.get('crop_name', f'Crop_{i+1}'))
                        crop_dict[crop_name] = crop_item
                    else:
                        crop_dict[f'Crop_{i+1}'] = {'name': str(crop_item)}
                crop_data = crop_dict
            elif not isinstance(crop_data, dict):
                st.sidebar.error("❌ Crop cycle data format not supported")
                return documents
            
            # Create overview document
            overview_content = f"""
CROP CYCLE KNOWLEDGE BASE OVERVIEW
==================================
Total Crops: {len(crop_data)} different crop varieties
Coverage: Complete crop cycle information including seasons, growth stages, and management practices

This knowledge base contains comprehensive agricultural information for crop planning,
seasonal guidance, and farming best practices across different crop varieties.
"""
            documents.append(Document(
                page_content=overview_content,
                metadata={"source": "crop_cycle_overview", "type": "overview", "category": "crop_cycle"}
            ))
            
            # Process each crop
            for crop_name, crop_info in crop_data.items():
                # Ensure crop_info is a dictionary
                if not isinstance(crop_info, dict):
                    crop_info = {'name': str(crop_info)}
                
                crop_content = f"""
COMPREHENSIVE CROP GUIDE: {crop_name.upper()}
{'='*60}
Crop Name: {crop_name}
Category: {crop_info.get('category', crop_info.get('type', 'General Agriculture'))}

SEASONAL INFORMATION:
Planting Season: {crop_info.get('planting_season', crop_info.get('sowing_season', crop_info.get('season', 'N/A')))}
Growing Period: {crop_info.get('growing_period', crop_info.get('duration', crop_info.get('growth_duration', 'N/A')))} days
Harvest Season: {crop_info.get('harvest_season', crop_info.get('harvesting_time', 'N/A'))}

SOIL REQUIREMENTS:
"""
                # Handle soil requirements (could be nested dict or simple values)
                soil_req = crop_info.get('soil_requirements', crop_info.get('soil', {}))
                if isinstance(soil_req, dict):
                    crop_content += f"""Soil Type: {soil_req.get('type', soil_req.get('soil_type', 'N/A'))}
pH Range: {soil_req.get('ph_range', soil_req.get('ph', 'N/A'))}
Drainage: {soil_req.get('drainage', 'N/A')}"""
                else:
                    crop_content += f"""Soil Type: {soil_req if soil_req else 'N/A'}
pH Range: N/A
Drainage: N/A"""

                crop_content += """

CLIMATE CONDITIONS:
"""
                # Handle climate information
                climate = crop_info.get('climate', crop_info.get('weather', {}))
                if isinstance(climate, dict):
                    crop_content += f"""Temperature: {climate.get('temperature', climate.get('temp', 'N/A'))}
Rainfall: {climate.get('rainfall', climate.get('precipitation', 'N/A'))}
Humidity: {climate.get('humidity', 'N/A')}"""
                else:
                    crop_content += f"""Temperature: {climate if climate else 'N/A'}
Rainfall: N/A
Humidity: N/A"""

                crop_content += """

GROWTH STAGES:
"""
                # Handle growth stages (could be list or dict)
                growth_stages = crop_info.get('growth_stages', crop_info.get('stages', []))
                if isinstance(growth_stages, list) and growth_stages:
                    for i, stage in enumerate(growth_stages, 1):
                        if isinstance(stage, dict):
                            stage_name = stage.get('stage', stage.get('name', f'Stage {i}'))
                            duration = stage.get('duration', stage.get('days', 'N/A'))
                            activities = stage.get('activities', stage.get('tasks', []))
                            
                            crop_content += f"""
Stage {i}: {stage_name}
Duration: {duration}
Key Activities: {', '.join(activities) if isinstance(activities, list) and activities else 'Standard care practices'}
"""
                        else:
                            crop_content += f"""
Stage {i}: {stage}
Duration: N/A
Key Activities: Standard care practices
"""
                elif isinstance(growth_stages, dict):
                    for stage_key, stage_info in growth_stages.items():
                        duration = stage_info.get('duration', 'N/A') if isinstance(stage_info, dict) else 'N/A'
                        crop_content += f"""
{stage_key}: {stage_info if isinstance(stage_info, str) else stage_key}
Duration: {duration}
"""
                else:
                    crop_content += "Standard crop growth stages apply\n"
                
                # Handle management practices
                management = crop_info.get('management_practices', crop_info.get('management', crop_info.get('practices', {})))
                if isinstance(management, dict) and management:
                    crop_content += f"""

MANAGEMENT PRACTICES:
Irrigation: {management.get('irrigation', management.get('watering', 'N/A'))}
Fertilization: {management.get('fertilization', management.get('fertilizer', 'N/A'))}
Pest Control: {management.get('pest_control', management.get('pest_management', 'N/A'))}
Weed Management: {management.get('weed_management', management.get('weeding', 'N/A'))}
"""
                
                # Handle yield information
                yield_info = crop_info.get('yield', crop_info.get('production', {}))
                if isinstance(yield_info, dict) and yield_info:
                    crop_content += f"""

YIELD INFORMATION:
Expected Yield: {yield_info.get('expected', yield_info.get('average', 'N/A'))} per {yield_info.get('unit', 'hectare')}
Factors Affecting Yield: {', '.join(yield_info.get('factors', ['Soil health', 'Weather', 'Management practices']))}
"""
                elif yield_info and not isinstance(yield_info, dict):
                    crop_content += f"""

YIELD INFORMATION:
Expected Yield: {yield_info}
"""
                
                # Handle economic information
                economic = crop_info.get('economics', crop_info.get('economy', crop_info.get('cost', {})))
                if isinstance(economic, dict) and economic:
                    crop_content += f"""

ECONOMIC CONSIDERATIONS:
Market Price Range: {economic.get('price_range', economic.get('price', 'N/A'))}
Investment Required: {economic.get('investment', economic.get('cost', 'N/A'))}
Profit Margin: {economic.get('profit_margin', economic.get('profit', 'N/A'))}
"""
                
                # Handle regional suitability
                regions = crop_info.get('suitable_regions', crop_info.get('regions', crop_info.get('areas', [])))
                if isinstance(regions, list) and regions:
                    crop_content += f"""

REGIONAL SUITABILITY:
Best Suited Regions: {', '.join(regions)}
"""
                elif regions and not isinstance(regions, list):
                    crop_content += f"""

REGIONAL SUITABILITY:
Best Suited Regions: {regions}
"""
                
                crop_content += f"""

FARMING RECOMMENDATIONS:
This crop guide provides essential information for farmers planning to cultivate {crop_name}.
Success depends on following the recommended practices, understanding local conditions,
and adapting techniques based on regional requirements and market conditions.
"""
                
                documents.append(Document(
                    page_content=crop_content,
                    metadata={
                        "source": f"crop_{crop_name.lower().replace(' ', '_')}",
                        "type": "crop_guide",
                        "category": "crop_cycle",
                        "crop_name": crop_name,
                        "crop_category": crop_info.get('category', crop_info.get('type', 'general'))
                    }
                ))
                
        except Exception as e:
            st.error(f"Error loading crop cycle JSON: {e}")
        
        return documents

# --- Main App Logic ---
st.title("🌱 AI Soil & Agriculture Assistant")
st.markdown("""
**Complete Agricultural Intelligence System**

Get comprehensive farming advice combining:
- 🧪 **Detailed Soil Analysis** for Tamil Nadu & Kerala (16 major cities)
- 🌾 **Government Schemes** and agricultural policies  
- 📊 **10+ Soil Parameters** including pH, nutrients, organic matter
- 🚜 **Crop Recommendations** based on actual soil conditions
- 🌿 **Crop Cycle Management** with seasonal guidance
""")

# --- Sidebar for Configuration ---
with st.sidebar:
    st.header("🔧 Configuration")
    
    # Check knowledge bases
    kb_status = []
    
    if SOIL_KB_PATH:
        st.success(f"✅ Soil Knowledge Base Found")
        st.code(f"Path: {SOIL_KB_PATH}")
        kb_status.append("soil")
        
        # Verify contents
        json_exists = os.path.exists(os.path.join(SOIL_KB_PATH, "complete_soil_knowledge_base.json"))
        docs_exist = os.path.exists(os.path.join(SOIL_KB_PATH, "documents"))
        try:
            csv_files = [f for f in os.listdir(SOIL_KB_PATH) if f.endswith('.csv')]
            csv_count = len(csv_files)
        except:
            csv_count = 0
        
        st.info(f"""
**📊 Soil Data Available:**
- Soil Database: {'✅' if json_exists else '❌'}
- Analysis Reports: {'✅' if docs_exist else '❌'}  
- Data Tables: {csv_count} CSV files
        """)
    else:
        st.error("❌ Soil Knowledge Base Not Found")
    
    if CROP_CYCLE_KB_PATH:
        st.success(f"✅ Crop Cycle Knowledge Base Found")
        st.code(f"Path: {CROP_CYCLE_KB_PATH}")
        kb_status.append("crop_cycle")
        
        # Verify crop cycle contents
        crop_json_exists = os.path.exists(os.path.join(CROP_CYCLE_KB_PATH, "crop_cycle.json"))
        st.info(f"""
**🌿 Crop Cycle Data Available:**
- Crop Database: {'✅' if crop_json_exists else '❌'}
        """)
    else:
        st.error("❌ Crop Cycle Knowledge Base Not Found")
        st.markdown("**Searched locations:**")
        for path in POSSIBLE_CROP_CYCLE_PATHS:
            st.code(f"❌ {path}")
    
    st.info(f"""
**🌐 Additional Sources:**
- Web Sources: {len(FARMER_URLS)} URLs
    """)
    
    # API Key configuration
    try:
        groq_api_key = os.environ["GROQ_API_KEY"]
        st.success("✅ Groq API Key loaded from environment")
    except KeyError:
        groq_api_key = st.text_input("🔑 Enter your Groq API Key:", type="password")
        if not groq_api_key:
            st.error("Please provide your Groq API Key to continue.")
            st.stop()
    
    # Model selection
    available_models = [
        "llama-3.1-8b-instant",
        "llama-3.3-70b-versatile", 
        "gemma2-9b-it"
    ]
    
    selected_model = st.selectbox(
        "🤖 Select AI Model:",
        available_models,
        index=0,
        help="Choose the language model for agricultural analysis"
    )

# --- Enhanced Session State Initialization ---
if "vectors" not in st.session_state:
    with st.spinner("🔨 Building comprehensive agricultural knowledge base..."):
        try:
            MODEL_PATH = Path(__file__).parent.parent / "models" / "bge-small-en-v1.5"
            @st.cache_resource(show_spinner="🔨 Loading embeddings...")



            def get_embeddings():
                return HuggingFaceEmbeddings(model_name=str(MODEL_PATH))
            # Initialize embeddings
            embeddings=get_embeddings()
            
            all_documents = []
            
            # 1. Load soil knowledge base if available
            if SOIL_KB_PATH:
                loader = SoilKnowledgeLoader(SOIL_KB_PATH)
                soil_documents = loader.load_all_documents()
                all_documents.extend(soil_documents)
                st.sidebar.info(f"📊 Loaded {len(soil_documents)} soil documents")
            
            # 2. Load crop cycle knowledge base if available
            if CROP_CYCLE_KB_PATH:
                crop_loader = CropCycleKnowledgeLoader(CROP_CYCLE_KB_PATH)
                crop_documents = crop_loader.load_all_documents()
                all_documents.extend(crop_documents)
                st.sidebar.info(f"🌿 Loaded {len(crop_documents)} crop cycle documents")
            
            # 3. Load web-based farming information
            try:
                @st.cache_data(ttl=86400)  # cache for 1 day
                def fetch_web_documents():
                    try:
                        loader = WebBaseLoader(FARMER_URLS)
                        return loader.load()
                    except Exception as e:
                        return []
                
                
                web_documents = fetch_web_documents()
                
                # Enhance web document metadata
                for doc in web_documents:
                    doc.metadata.update({
                        "category": "farming_schemes",
                        "type": "government_info",
                        "data_format": "web"
                    })
                
                all_documents.extend(web_documents)
                st.sidebar.info(f"🌐 Loaded {len(web_documents)} web documents")
            except Exception as e:
                st.sidebar.warning(f"⚠️ Web loading issue: {e}")
            
            if not all_documents:
                st.error("No documents could be loaded! Please check your knowledge base and internet connection.")
                st.stop()
            
            # 4. Process all documents
            @st.cache_resource(show_spinner="🔨 Building FAISS index...")
            def build_vectorstore(documents, embeddings):
                text_splitter = RecursiveCharacterTextSplitter(
                    chunk_size=1200,
                    chunk_overlap=200,
                    separators=["\n\n", "\n", ".", " "]
                )
                final_docs = text_splitter.split_documents(documents)
                vectors = FAISS.from_documents(final_docs, embeddings)
                return vectors, final_docs
            
            # Build vectorstore
            vectors, final_documents = build_vectorstore(all_documents, embeddings)
            st.session_state.vectors = vectors
            
            # Summary stats
            soil_docs = len([d for d in final_documents if d.metadata.get("category", "").startswith("soil")])
            crop_docs = len([d for d in final_documents if d.metadata.get("category") == "crop_cycle"])
            scheme_docs = len([d for d in final_documents if d.metadata.get("category") == "farming_schemes"])
            
            st.sidebar.success(f"""
✅ **Knowledge Base Ready!**
- Total chunks: {len(final_documents)}
- Soil data: {soil_docs} chunks  
- Crop cycles: {crop_docs} chunks
- Schemes/Web: {scheme_docs} chunks
            """)
            
        except Exception as e:
            st.error(f"❌ Failed to build knowledge base: {e}")
            st.stop()

# --- Enhanced RAG Chain Setup ---
if "vectors" in st.session_state:
    try:
        # Initialize LLM
        llm = ChatGroq(
            groq_api_key=groq_api_key,
            model_name=selected_model
        )

        # Enhanced prompt template with soil parameter ranges
        prompt_template = ChatPromptTemplate.from_template("""
CRITICAL NORMALIZATION RULES - APPLY BEFORE ANY RESPONSE:

When you encounter soil parameter values, AUTOMATICALLY normalize them to realistic ranges:
• Clay content >100%: divide by 10 (e.g., 311% → 31.1%)
• Sand/Silt content >100%: divide by 10 
• pH >10: divide by 10 (e.g., 59.1 → 5.91)
• Nitrogen >10 g/kg: divide by 100 (e.g., 323.89 → 3.24 g/kg)
• Any percentage >100%: normalize to realistic range

NEVER mention the original incorrect values. ONLY show normalized values.
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

You are an expert agricultural advisor with comprehensive knowledge of:
1. Soil science and soil health analysis for Tamil Nadu and Kerala
2. Crop cycle management, seasonal planning, and growth stages
3. Indian government agricultural schemes and policies  
4. Crop recommendations based on scientific soil data and seasonal patterns
5. Sustainable farming practices and integrated crop management

RESPONSE RULES:
- For SOIL questions: Show only normalized soil values + crop recommendations. No schemes.
- For SCHEME questions: Explain only the scheme details. No soil data.
- For BOTH soil+schemes: Separate into two clear sections.
- Focus only on the most relevant parameters for the crop/question asked.
- Keep interpretations concise (1-2 lines per parameter).

Use the provided context to answer questions about:
• Soil conditions, pH, nutrients, and agricultural properties
• Crop selection, planting seasons, and growth cycle management  
• Seasonal farming calendar and crop rotation planning
• Government schemes, subsidies, and farmer support programs
• Agricultural loans, insurance, and financial assistance
• Best farming practices for specific soil and crop combinations
• Pest management, fertilization, and irrigation scheduling

When discussing soil data, reference specific measurements and cities when available.
For crop cycles, provide seasonal guidance and growth stage information.
For government schemes, provide current and actionable information.
Always give practical, farmer-friendly advice that can be implemented.

<context>
{context}
</context>

Question: {input}

Provide a comprehensive, practical answer with only realistic, normalized soil values:
""")



        # Create enhanced retrieval chain
        document_chain = create_stuff_documents_chain(llm, prompt_template)
        retriever = st.session_state.vectors.as_retriever(
            search_type="similarity",
            search_kwargs={"k": 8}  # Retrieve more context for complex queries
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
        
        # --- Enhanced Sample Questions ---
        st.markdown("### 💡 What You Can Ask:")
        
        # Organize questions by category
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("**🧪 Soil & Location:**")
            soil_questions = [
                "What is the soil pH in Chennai and what crops are suitable?",
                "Compare soil organic carbon between Coimbatore and Kochi", 
                "Which Kerala cities have clay soils good for rice farming?",
            ]
            
            for i, q in enumerate(soil_questions):
                if st.button(q, key=f"soil_{i}"):
                    st.session_state.sample_question = q
        
        with col2:
            st.markdown("**🌿 Crop Cycles:**")  
            crop_questions = [
                "When should I plant rice in Tamil Nadu?",
                "What are the growth stages of wheat cultivation?",
                "Best crop rotation for improving soil health?",
            ]
            
            for i, q in enumerate(crop_questions):
                if st.button(q, key=f"crop_{i}"):
                    st.session_state.sample_question = q
        
        with col3:
            st.markdown("**🏛️ Government Schemes:**")  
            scheme_questions = [
                "What is the PM-KISAN scheme and how to apply?",
                "How to get agricultural loans for small farmers?",
                "What crop insurance schemes are available?",
            ]
            
            for i, q in enumerate(scheme_questions):
                if st.button(q, key=f"scheme_{i}"):
                    st.session_state.sample_question = q
        
        # --- User Input and Response Generation ---
        user_prompt = None
        if hasattr(st.session_state, 'sample_question'):
            user_prompt = st.session_state.sample_question
            del st.session_state.sample_question
        
        prompt = st.chat_input("💬 Ask about soil conditions, crop cycles, seasonal planning, government schemes, or farming advice...")
        
        if user_prompt or prompt:
            question_to_process = user_prompt if user_prompt else prompt
            
            start_time = time.time()
            
            # Process query
            response = retrieval_chain.invoke({"input": question_to_process})
            
            end_time = time.time()
            response_time = round(end_time - start_time, 2)
            
            # Display results
            st.markdown(f"### 🌾 Question: *{question_to_process}*")
            
            st.markdown("### 🧠 Expert Response:")
            st.markdown(response['answer'])
            st.success(f"⚡ Generated in {response_time} seconds")
            
            # Enhanced context display
            with st.expander("📚 Retrieved Knowledge Sources"):
                # Categorize sources
                soil_sources = []
                crop_sources = []
                scheme_sources = []
                other_sources = []
                
                for doc in response['context']:
                    category = doc.metadata.get('category', '')
                    if category.startswith('soil') or category.startswith('city') or category.startswith('regional'):
                        soil_sources.append(doc)
                    elif category == 'crop_cycle':
                        crop_sources.append(doc)
                    elif category == 'farming_schemes':
                        scheme_sources.append(doc)
                    else:
                        other_sources.append(doc)
                
                if soil_sources:
                    st.markdown("**🧪 Soil Data Sources:**")
                    for i, doc in enumerate(soil_sources, 1):
                        source_name = doc.metadata.get('source', f'Source {i}')
                        st.markdown(f"*{i}. {source_name}*")
                        st.markdown(f"> {doc.page_content[:400]}...")
                        st.markdown("---")
                
                if crop_sources:
                    st.markdown("**🌿 Crop Cycle Sources:**")
                    for i, doc in enumerate(crop_sources, 1):
                        crop_name = doc.metadata.get('crop_name', 'Crop Guide')
                        st.markdown(f"*{i}. {crop_name}*")
                        st.markdown(f"> {doc.page_content[:400]}...")
                        st.markdown("---")
                
                if scheme_sources:
                    st.markdown("**🏛️ Government Scheme Sources:**") 
                    for i, doc in enumerate(scheme_sources, 1):
                        source_url = doc.metadata.get('source', 'Web Source')
                        st.markdown(f"*{i}. {source_url}*")
                        st.markdown(f"> {doc.page_content[:400]}...")
                        st.markdown("---")
                
                if other_sources:
                    st.markdown("**📖 Additional Sources:**")
                    for i, doc in enumerate(other_sources, 1):
                        source_name = doc.metadata.get('source', f'Other {i}')
                        st.markdown(f"*{i}. {source_name}*")
                        st.markdown(f"> {doc.page_content[:300]}...")
                        st.markdown("---")

    except Exception as e:
        st.error(f"❌ Error: {e}")
        
        if "model" in str(e).lower() and "decommissioned" in str(e).lower():
            st.error("⚠️ Selected model unavailable. Try a different model.")

# --- Enhanced Knowledge Base Statistics Dashboard ---
with st.expander("📊 Knowledge Base Statistics"):
    col1, col2, col3, col4 = st.columns(4)
    
    # Soil Knowledge Base Stats
    if SOIL_KB_PATH:
        try:
            json_path = os.path.join(SOIL_KB_PATH, "complete_soil_knowledge_base.json")
            if os.path.exists(json_path):
                with open(json_path, 'r') as f:
                    kb_data = json.load(f)
                
                metadata = kb_data.get('metadata', {})
                regions = kb_data.get('regions', {})
                
                with col1:
                    st.metric("🗺️ States", len(regions))
                    st.metric("📊 Soil Parameters", metadata.get('total_parameters', 10))
                
                with col2:
                    total_cities = sum(len(r.get('city_profiles', {})) for r in regions.values())
                    st.metric("🏙️ Cities Analyzed", total_cities)
                    st.metric("📏 Depth Layers", metadata.get('depth_layers', 6))
                
        except Exception as e:
            st.error(f"Error loading soil statistics: {e}")
    
    # Crop Cycle Knowledge Base Stats
    if CROP_CYCLE_KB_PATH:
        try:
            crop_json_path = os.path.join(CROP_CYCLE_KB_PATH, "crop_cycle.json")
            if os.path.exists(crop_json_path):
                with open(crop_json_path, 'r') as f:
                    crop_data = json.load(f)
                
                with col3:
                    st.metric("🌿 Crop Varieties", len(crop_data))
                    
                    # Count categories
                    categories = set()
                    for crop_info in crop_data.values():
                        if 'category' in crop_info:
                            categories.add(crop_info['category'])
                    
                    st.metric("📂 Crop Categories", len(categories))
                
        except Exception as e:
            st.error(f"Error loading crop cycle statistics: {e}")
    
    with col4:
        st.metric("🎯 Resolution", "250m")
        st.metric("🌐 Web Sources", len(FARMER_URLS))
    
    # Detailed data source info
    st.markdown("**📋 Comprehensive Data Sources:**")
    
    sources_info = []
    if SOIL_KB_PATH:
        sources_info.append("• **Soil Data:** SoilGrids 2.0 (Tamil Nadu & Kerala coverage)")
    if CROP_CYCLE_KB_PATH:
        sources_info.append("• **Crop Cycles:** Comprehensive crop management database")
    sources_info.extend([
        "• **Government Schemes:** Vikaspedia, India.gov.in agricultural portals",
        "• **Regional Focus:** South Indian agricultural systems and practices"
    ])
    
    for source in sources_info:
        st.markdown(source)

# --- Footer with additional information ---
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; font-size: 0.9em;'>
🌱 AI Soil & Agriculture Assistant - Comprehensive farming intelligence for sustainable agriculture<br>
Combining soil science, crop management, and government policy information for informed farming decisions
</div>
""", unsafe_allow_html=True)
