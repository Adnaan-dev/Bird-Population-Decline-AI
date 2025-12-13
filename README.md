# 🦅 Bird Population Decline AI

> **Advanced Geospatial Intelligence Platform for Habitat Monitoring**

A cutting-edge web application that leverages satellite imagery, deep learning, and real-time weather data to analyze bird habitat health and predict population decline risk. Built with Streamlit, PyTorch, and Sentinel-2 satellite data.

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.x-red.svg)](https://streamlit.io/)
[![PyTorch](https://img.shields.io/badge/PyTorch-0.14+-orange.svg)](https://pytorch.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## 🌟 Features

### 🗺️ **Interactive Map Analysis**
- Click on any location on the satellite map to analyze bird habitat
- Real-time processing of Sentinel-2 multispectral imagery
- Instant results with vegetation, water, and urban indices

### 📊 **Satellite Data Processing**
- **NDVI** (Normalized Difference Vegetation Index) - Vegetation health
- **NDWI** (Normalized Difference Water Index) - Water body detection
- **NDBI** (Normalized Difference Built Index) - Urban development tracking
- Multi-spectral band analysis (Blue, Green, Red, Near-Infrared)

### 🤖 **AI-Powered Classification**
- ResNet18 deep learning model for land-cover classification
- Automatic detection of Forest, Urban, and Water areas
- Habitat suitability scoring for bird populations

### 📈 **Time-Series Analysis**
- Track vegetation health trends over 1-365+ days
- Identify seasonal patterns and long-term degradation
- Historical satellite data comparison

### 🌡️ **Real-Time Weather Integration**
- Current temperature, humidity, wind speed
- Cloud coverage and pressure data
- Essential for understanding habitat conditions

### 🎨 **Modern Glassmorphism UI**
- Professional dark theme with gradient colors
- Smooth animations and hover effects
- Responsive design for desktop and tablet
- Interactive visualizations and heatmaps

### 📊 **Comprehensive Metrics**
- Habitat Health Score (0-100%)
- Bird Population Decline Risk Level (Low/Medium/High)
- Land-cover percentage breakdown
- NDVI, NDWI, NDBI value analysis

---

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- pip or conda
- Internet connection (for API calls)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/bird-population-decline-ai.git
   cd bird-population-decline-ai
   ```

2. **Create virtual environment** (recommended)
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure API Keys**
   
   Create a `.env` file in the project root:
   ```env
   MAPBOX_ACCESS_TOKEN=your_mapbox_token_here
   OPENWEATHER_API_KEY=your_openweather_key_here
   SENTINEL_CLIENT_ID=your_sentinel_client_id_here
   SENTINEL_CLIENT_SECRET=your_sentinel_client_secret_here
   ```

5. **Run the application**
   ```bash
   streamlit run app.py
   ```
   
   The app will open at `http://localhost:8501`

---

## 🔧 API Setup

### 1. **Sentinel Hub** (Satellite Data)
- Sign up at [Sentinel Hub](https://www.sentinel-hub.com/)
- Create OAuth client credentials
- Note your Client ID and Secret

### 2. **OpenWeather API** (Weather Data)
- Get free API key at [OpenWeather](https://openweathermap.org/api)
- Free tier: 1000 calls/day
- Supports 60+ weather parameters

### 3. **Mapbox** (Satellite Maps)
- Create account at [Mapbox](https://www.mapbox.com/)
- Generate access token in Account settings
- Free tier: 25,000 monthly vector tiles

---

## 📚 Usage Guide

### **Module 1: Map Analysis** 📍

1. Navigate to **"📍 Map Analysis"** in the sidebar
2. **Click on the map** to select a location (any latitude/longitude)
3. Wait for data processing (5-15 seconds)
4. View results:
   - 🌿 **Key Metrics**: Habitat health, bird risk, NDVI values
   - 🛰️ **Satellite Imagery**: RGB, NDVI, NDWI, NDBI heatmaps
   - 🏙️ **Land-Cover Classification**: Forest/Urban/Water breakdown
   - 🌡️ **Weather Information**: Current weather conditions

**Example Locations:**
- Western Ghats, India: `14.13°N, 74.24°E`
- Amazon Rainforest, Brazil: `-3.00°S, -60.00°W`
- Everglades, USA: `25.35°N, -80.70°W`

### **Module 2: NDVI Time-Series** 📈

1. Navigate to **"📈 NDVI Time-Series"** in the sidebar
2. Select **Start Date** and **End Date** (up to 365 days)
3. Click **"📈 Compute NDVI Trend"**
4. View vegetation health trend over time
5. Analyze patterns:
   - Seasonal fluctuations
   - Long-term degradation/recovery
   - Impact of human activities

**Interpretation:**
- **Upward trend**: Vegetation recovery ✅
- **Downward trend**: Habitat degradation ❌
- **Seasonal pattern**: Natural cycles

### **Module 3: About** ℹ️

View technology stack and project information:
- Satellite data sources (Sentinel-2)
- Deep learning framework (PyTorch)
- Web framework (Streamlit)
- Geospatial tools (Folium, Mapbox)

---

## 📊 Technical Architecture

```
┌─────────────────────────────────────┐
│     Streamlit Web Interface         │
│  (Interactive Map + User Controls)  │
└────────────────┬────────────────────┘
                 │
        ┌────────┴────────┐
        │                 │
   ┌────▼────┐      ┌─────▼──────┐
   │Sentinel │      │ OpenWeather│
   │Hub API  │      │   API      │
   │         │      │            │
   └────┬────┘      └─────┬──────┘
        │                 │
        └────────┬────────┘
                 │
        ┌────────▼────────┐
        │ Data Processing │
        │  (NumPy/PIL)    │
        └────────┬────────┘
                 │
        ┌────────▼────────┐
        │  NDVI/NDWI/NDBI │
        │  Calculation    │
        └────────┬────────┘
                 │
        ┌────────▼────────┐
        │ ResNet18 Model  │
        │ (PyTorch)       │
        └────────┬────────┘
                 │
        ┌────────▼────────┐
        │ Visualization   │
        │ (Matplotlib)    │
        └────────┬────────┘
                 │
        ┌────────▼────────┐
        │   UI Display    │
        │ (Glassmorphism) │
        └─────────────────┘
```

---

## 🛠️ Project Structure

```
bird-population-decline-ai/
├── app.py                          # Main Streamlit application
├── config.py                       # Configuration settings
├── model_loader.py                 # Model loading utilities
├── model_utils.py                  # Model processing utilities
├── predictor.py                    # Prediction pipeline
├── sentinel_utils.py               # Sentinel Hub API integration
├── requirements.txt                # Python dependencies
├── bird_decline_model.pth          # Pre-trained model weights
├── ui_style.css                    # Custom CSS styling
├── static/
│   └── index.html                  # Landing page
├── .env                            # Environment variables (create this)
├── .gitignore                      # Git ignore file
├── README.md                       # This file
├── WEB_APP_REPORT.md               # Detailed technical report
└── __pycache__/                    # Python cache
```

---

## 📦 Dependencies

### Core Libraries
```
streamlit>=1.0.0
torch>=0.14.0
torchvision>=0.15.0
numpy>=1.20.0
matplotlib>=3.5.0
pillow>=8.0.0
requests>=2.28.0
rasterio>=1.3.0
```

### Geospatial & Mapping
```
folium>=0.14.0
streamlit-folium>=0.6.0
pyproj>=3.0.0
```

### Utilities
```
python-dotenv>=0.19.0
fpdf2>=2.7.8
```

**See [requirements.txt](requirements.txt) for complete list**

---

## 🔬 Algorithm Details

### NDVI (Vegetation Health)
```
NDVI = (NIR - RED) / (NIR + RED)
Range: -1.0 to +1.0
- High (0.7+): Dense, healthy vegetation ✅
- Medium (0.4-0.6): Moderate vegetation
- Low (<0.3): Poor/no vegetation ❌
```

### NDWI (Water Detection)
```
NDWI = (GREEN - NIR) / (GREEN + NIR)
Range: -1.0 to +1.0
- Positive (0.3-1.0): Water bodies 💧
- Negative: Vegetation/dry areas
```

### NDBI (Urban Detection)
```
NDBI = (SWIR - NIR) / (SWIR + NIR)
Range: -1.0 to +1.0
- Positive: Urban/built-up areas 🏙️
- Negative: Natural vegetation
```

### Habitat Health Score
```
Score = (NDVI × 40%) + (Water × 30%) - (Urban × 30%)
Rating:
- 70-100: Excellent habitat ⭐⭐⭐
- 50-70: Good habitat ⭐⭐
- 30-50: Fair habitat ⭐
- 0-30: Poor habitat ❌
```

---

## 🎨 UI/UX Features

### Design Philosophy
- **Glassmorphism**: Frosted glass effect with backdrop blur
- **Dark Theme**: Reduces eye strain, modern aesthetic
- **Gradient Colors**: Green (#10b981) → Cyan (#06b6d4) → Yellow-Green (#4ade80)
- **Smooth Animations**: 0.3s transitions, hover effects
- **Responsive Layout**: Works on desktop, tablet, mobile

### Color Palette
| Element | Color | Hex |
|---------|-------|-----|
| Primary | Emerald Green | #10b981 |
| Secondary | Cyan | #06b6d4 |
| Accent | Lime Green | #4ade80 |
| Background | Dark Slate | #0f172a |
| Text | Light Gray | #e5e7eb |

---

## ⚡ Performance

| Operation | Time | Notes |
|-----------|------|-------|
| Satellite fetch | 3-8s | Sentinel Hub API |
| Index calculation | 1-2s | NDVI/NDWI/NDBI |
| Model inference | 0.5-1s | ResNet18 forward pass |
| Visualization | 1-3s | Matplotlib rendering |
| **Total per click** | **5-15s** | End-to-end processing |
| **Time-series (365 days)** | **20-40s** | Multiple API calls |

### Infrastructure Requirements
- **CPU**: 4+ cores
- **RAM**: 8 GB (16 GB recommended)
- **Storage**: 10 GB
- **Network**: 100+ Mbps

---

## 🚀 Deployment

### **Streamlit Cloud** (Easiest)
```bash
# Push to GitHub, then link in Streamlit Cloud
# https://streamlit.io/cloud
```

### **Docker**
```bash
docker build -t bird-decline-ai .
docker run -p 8501:8501 bird-decline-ai
```

### **AWS EC2**
```bash
# Launch Ubuntu instance
sudo apt update && sudo apt install python3-pip
pip install -r requirements.txt
streamlit run app.py
```

### **Google Cloud Run**
```bash
gcloud run deploy bird-decline-ai --source .
```

---

## 📖 Documentation

- [WEB_APP_REPORT.md](WEB_APP_REPORT.md) - Comprehensive technical report
- [Sentinel Hub Docs](https://www.sentinel-hub.com/develop/)
- [OpenWeather API](https://openweathermap.org/api)
- [Mapbox Documentation](https://docs.mapbox.com/)
- [PyTorch Docs](https://pytorch.org/docs/)
- [Streamlit Guide](https://docs.streamlit.io/)

---

## 🤝 Contributing

Contributions are welcome! Here's how to contribute:

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. **Commit** your changes (`git commit -m 'Add amazing feature'`)
4. **Push** to the branch (`git push origin feature/amazing-feature`)
5. **Open** a Pull Request

### Development Setup
```bash
git clone https://github.com/yourusername/bird-population-decline-ai.git
cd bird-population-decline-ai
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

### Code Guidelines
- Follow PEP 8 style guide
- Add comments for complex logic
- Include docstrings for functions
- Test before submitting PR

---

### Workarounds
- Select dates with lower cloud cover
- Fine-tune model on labeled data for production
- Implement request caching for repeated queries
- Use VPN if rate-limited by APIs

---

## 📋 Roadmap

### v2.1 (Q1 2026)
- [ ] Database integration for historical caching
- [ ] Multi-location comparison tool
- [ ] Batch processing API
- [ ] Mobile app (React Native)

### v2.2 (Q2 2026)
- [ ] Advanced filtering (by season, weather)
- [ ] GBIF bird sighting integration
- [ ] Custom area drawing on map
- [ ] Export to GeoJSON/Shapefile

### v3.0 (Q3 2026)
- [ ] Real-time monitoring alerts
- [ ] Drone imagery integration
- [ ] Advanced ML model fine-tuning
- [ ] International language support

---

## 📄 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

---

## 👥 Authors

- **Developed by**: Development Team
- **Version**: 2.0
- **Last Updated**: December 13, 2025

---

## 📧 Support & Contact

- **Issues**: [GitHub Issues](https://github.com/yourusername/bird-population-decline-ai/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/bird-population-decline-ai/discussions)
- **Email**: support@example.com

---

## 🙏 Acknowledgments

This project utilizes:
- **Sentinel-2 data** from European Commission Copernicus Programme
- **OpenWeather** for real-time weather data
- **Mapbox** for satellite basemaps
- **PyTorch team** for the deep learning framework
- **Streamlit** team for the amazing web framework

---

## 🔗 Related Resources

- [Sentinel Hub](https://www.sentinel-hub.com/) - Satellite data access
- [Copernicus Programme](https://www.copernicus.eu/) - Earth observation
- [eBird Database](https://ebird.org/) - Bird sighting records
- [GBIF](https://www.gbif.org/) - Biodiversity data
- [Conservation International](https://www.conservation.org/) - Conservation insights

---

## ⭐ Star us!

If you find this project useful, please give it a ⭐ on GitHub!

```
Made by Adnan with ❤️ using Streamlit, Sentinel-2 & PyTorch
```

---

**Last Updated**: December 13, 2025 | **Status**: ✅ Production Ready
