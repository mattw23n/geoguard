# 🛡️ GeoGuard Professional Web Interface

## Overview

The GeoGuard Streamlit UI provides a comprehensive, user-friendly interface for all core system features. This professional web application allows users to:

- Classify individual features
- Process batches of features
- View audit trails and analytics
- Monitor system health
- Access documentation

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Environment Variables

Create a `.env` file:

```env
GEMINI_API_KEY=your_gemini_api_key_here
```

### 3. Launch the UI

```bash
# Option 1: Using Makefile
make ui

# Option 2: Direct command
streamlit run ui/streamlit_app.py

# Option 3: From any directory
cd geoguard && streamlit run ui/streamlit_app.py
```

### 4. Access the Application

Open your browser to: `http://localhost:8501`

## 🎯 Features

### 🔍 Single Classification

- **Interactive Form**: Input feature details with helpful examples
- **Real-time Classification**: Get instant YES/NO/REVIEW decisions
- **Detailed Analysis**: View reasoning, evidence, regulations, and metadata
- **Quick Examples**: Pre-loaded test cases for demonstration

### 📊 Batch Processing

- **Dataset Management**: View and manage your synthetic dataset
- **One-Click Processing**: Process all features with a single button
- **Results Download**: Download CSV results directly from the UI
- **Analytics Dashboard**: Visual charts showing decision distributions and confidence scores

### 📋 Audit Trail

- **Complete History**: View all classification decisions
- **Timeline Analysis**: Interactive timeline of classification activity
- **Detailed Logs**: Expandable entries showing full decision context
- **Metrics Dashboard**: Summary statistics and performance indicators

### ⚙️ System Status

- **Health Checks**: Monitor all system components
- **Environment Info**: Check Python version, dependencies, API keys
- **Performance Stats**: View average confidence scores by decision type
- **File Verification**: Ensure all required data files are present

### 📚 Documentation

- **Complete Guide**: Overview, usage instructions, API reference
- **Quick Start**: Step-by-step setup and testing instructions
- **Examples**: Real-world use cases and test scenarios
- **API Reference**: Complete input/output schema documentation

## 🎨 UI Features

### Professional Design

- **Modern Styling**: Clean, professional interface with custom CSS
- **Responsive Layout**: Works on desktop and tablet devices
- **Color-Coded Results**: Visual indication of decision types
- **Interactive Charts**: Plotly-powered analytics and visualizations

### User Experience

- **Navigation Sidebar**: Easy access to all features
- **Progress Indicators**: Visual feedback during processing
- **Error Handling**: Graceful error messages and recovery
- **Download Capabilities**: Export results directly from the interface

### Accessibility

- **Clear Typography**: Easy-to-read fonts and sizing
- **Consistent Layout**: Predictable interface patterns
- **Help Text**: Contextual assistance throughout the application
- **Status Messages**: Clear feedback on all operations

## 🔧 Technical Details

### Architecture

- **Streamlit Framework**: Modern Python web framework
- **Plotly Integration**: Interactive charts and visualizations
- **Pandas Integration**: Data processing and CSV handling
- **Path Management**: Robust file and directory handling

### Performance

- **Caching**: Streamlit caching for improved performance
- **Async Processing**: Non-blocking operations where possible
- **Memory Efficient**: Optimized data loading and processing
- **Error Recovery**: Graceful handling of failed operations

### Security

- **Environment Variables**: Secure API key management
- **Input Validation**: Sanitized user inputs
- **File Safety**: Protected file operations
- **Session Management**: Secure session handling

## 📋 Usage Examples

### Example 1: Legal Compliance Feature

```
Feature ID: F-001
Feature Name: Utah Curfew Compliance
Description: To comply with the Utah Social Media Regulation Act, we implement a curfew-based login restriction for minors.

Expected Result: YES (Legal compliance required)
```

### Example 2: Business Geofence

```
Feature ID: F-002
Feature Name: Korea A/B Test
Description: A/B test dark theme accessibility for users in South Korea. Rollout is limited via GH and monitored with FR flags.

Expected Result: NO (Business-driven geofence)
```

### Example 3: Ambiguous Case

```
Feature ID: F-003
Feature Name: Global Filter Restriction
Description: Feature is available in all regions except Korea; no legal rationale stated.

Expected Result: REVIEW (Requires human evaluation)
```

## 🚨 Troubleshooting

### Common Issues

**UI Won't Start**

- Ensure all dependencies are installed: `pip install -r requirements.txt`
- Check that you're in the correct directory
- Verify Python version compatibility (3.11+)

**Classification Errors**

- Verify Gemini API key is set in `.env` file
- Check internet connection for API calls
- Ensure all data files are present in `/data` directory

**Import Errors**

- Run from the geoguard root directory
- Check that all app modules are present
- Verify Python path configuration

### Performance Tips

- Use batch processing for multiple features
- Close unused browser tabs to free memory
- Restart the UI if performance degrades

## 🔗 Integration

### API Backend

The UI integrates seamlessly with the FastAPI backend:

- **Shared Modules**: Uses the same classification engine
- **Consistent Results**: Identical output to API endpoints
- **Audit Integration**: Shares the same audit trail system

### Data Pipeline

- **Input Compatibility**: Uses same data formats as batch scripts
- **Output Consistency**: Generates identical CSV results
- **File Management**: Integrates with existing file structure

## 📊 Analytics & Monitoring

### Built-in Analytics

- Decision distribution pie charts
- Confidence score histograms
- Timeline analysis with filtering
- Performance metrics dashboard

### Export Capabilities

- CSV results download
- JSON audit logs
- Chart image exports
- Full data dumps

## 🎯 Demo Scenarios

### For Demonstrations

1. **Single Classification Demo**:

   - Use provided examples
   - Show real-time classification
   - Explain decision reasoning

2. **Batch Processing Demo**:

   - Load synthetic dataset
   - Run batch classification
   - Show results analytics

3. **Audit Trail Demo**:
   - Review classification history
   - Show timeline analysis
   - Explain traceability features

### For Testing

1. Test all example scenarios
2. Verify batch processing works
3. Check audit trail generation
4. Confirm system status reporting

The GeoGuard UI provides a complete, professional interface that makes the powerful compliance detection system accessible to all users, from technical teams to business stakeholders.
