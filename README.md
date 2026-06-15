# Digital Activity Flow System

A full-stack analytics dashboard for tracking user activity sessions across apps, devices, and categories. Monitor productivity, set daily goals, and visualize usage patterns with an interactive web dashboard powered by Flask and SQL Server.

## 📋 Overview

Digital Activity Flow System is an enterprise-grade analytics solution that tracks digital activity sessions in real-time. It helps users understand their app usage patterns, meet daily activity goals, and analyze productivity across different devices and applications.

## ✨ Features

- **User Management**: Create, read, update, and delete user profiles with customizable daily goals
- **Session Tracking**: Log digital activity sessions with detailed metadata (app, device, category, duration)
- **Real-time Dashboard**: Interactive web UI displaying live analytics and usage metrics
- **Daily Goal Tracking**: Monitor progress toward personalized daily activity targets
- **Multi-Device Support**: Track activity across multiple devices with dedicated device management
- **App & Category Management**: Organize apps into categories for better analytics
- **Session Analytics**: View usage trends, top apps, category breakdowns, and more
- **RESTful API**: Comprehensive API endpoints for all CRUD operations
- **Health Monitoring**: Built-in health check endpoint for system status

## 🛠️ Tech Stack

- **Backend**: Flask (Python web framework) with CORS support
- **Database**: SQL Server with ODBC drivers
- **Frontend**: HTML5, CSS3, JavaScript (interactive dashboard)
- **API**: RESTful API with JSON responses

## 📦 Prerequisites

- Python 3.7+
- SQL Server (Express or higher) with SQLEXPRESS01 instance
- SQL Server ODBC Driver 17 or 18 for SQL Server
- `pyodbc` library for database connectivity
- `flask` and `flask-cors` for the web API

## 🚀 Installation & Setup

### 1. Clone or Download the Project
```bash
cd DigitalActivityFlowFinal
```

### 2. Install Python Dependencies
```bash
pip install flask flask-cors pyodbc
```

### 3. Verify SQL Server Connection
Before running the app, verify that SQL Server is running:
- Open Services (services.msc) on Windows
- Ensure "SQL Server (SQLEXPRESS01)" service is Running
- Verify the database "DigitalActivityFlowSystem" exists

Test the connection:
```bash
python db.py
```

Expected output:
```
✅ Connected!  Database: DigitalActivityFlowSystem  |  Server time: [timestamp]
```

### 4. Run the Flask Application
```bash
python app.py
```

The application will start on `http://localhost:5000`

### 5. Access the Dashboard
Open your browser and navigate to:
```
http://localhost:5000
```

## 📁 Project Structure

```
DigitalActivityFlowFinal/
├── app.py                    # Flask application with API endpoints
├── db.py                     # Database connection management
├── ProjectDashboard.html     # Interactive web dashboard UI
├── test.py                   # Test cases (currently empty)
└── README.md                 # This file
```

## 📡 API Endpoints

### Health & Status
- `GET /api/health` - Check system health and available database drivers

### Users Management
- `GET /api/users` - List all users with session statistics
- `POST /api/users` - Create a new user
- `PUT /api/users/<id>` - Update user profile
- `DELETE /api/users/<id>` - Delete a user
- `GET /api/users/next-id` - Get the next auto-assigned user ID
- `GET /api/users/list` - Get user list for dropdowns

### Sessions Management
- `GET /api/sessions` - List all sessions with details
- `POST /api/sessions` - Log a new activity session
- `PUT /api/sessions/<id>` - Update session details
- `DELETE /api/sessions/<id>` - Delete a session

### Reference Lists (for UI dropdowns)
- `GET /api/apps/list` - Get all available apps
- `GET /api/devices/list` - Get all available devices

## 💾 Database Schema

The system uses the following main tables:

- **Users**: User profiles with demographic info and daily goals
- **Sessions**: Activity session logs with duration and timestamps
- **Apps**: Application registry
- **Devices**: Device registry
- **Categories**: Activity categories
- **AppCategory**: Many-to-many mapping of apps to categories

## ⚙️ Configuration

### Database Connection
Edit `db.py` to modify:
- `SERVER`: SQL Server instance name (default: `DESKTOP-JGD7VJ0\SQLEXPRESS01`)
- `DATABASE`: Database name (default: `DigitalActivityFlowSystem`)
- `DRIVERS`: List of ODBC drivers to try (auto-fallback supported)

### Flask Configuration
In `app.py`:
- CORS is enabled for all origins (`CORS(app, origins="*")`)
- Jinja2 delimiters are customized to prevent conflicts with JavaScript templating

## 🔧 Troubleshooting

### "Could not connect to SQL Server"
1. Check if SQL Server service is running (Services → SQL Server SQLEXPRESS01)
2. Verify ODBC drivers are installed: `odbcad32` in Windows
3. Confirm database name and server name match configuration
4. Check connection timeout settings in `db.py`

### "User not found" or "Session not found"
- Verify the entity exists before performing updates or deletes
- Use the list endpoints to confirm IDs

### CORS Issues
If frontend and backend are on different origins, CORS is already configured to allow all origins.

## 📝 Usage Examples

### Create a User
```bash
curl -X POST http://localhost:5000/api/users \
  -H "Content-Type: application/json" \
  -d '{
    "fullName": "John Doe",
    "email": "john@example.com",
    "age": 28,
    "city": "New York",
    "dailyGoalMin": 120
  }'
```

### Log a Session
```bash
curl -X POST http://localhost:5000/api/sessions \
  -H "Content-Type: application/json" \
  -d '{
    "userID": 1,
    "appID": 1,
    "deviceID": 1,
    "durationMinutes": 45,
    "startTime": "2026-06-16 10:30:00",
    "notes": "Morning productivity session"
  }'
```

### Get All Users
```bash
curl http://localhost:5000/api/users
```

## 📊 Dashboard Features

The interactive dashboard (`ProjectDashboard.html`) provides:
- User statistics and management interface
- Real-time session tracking
- Daily goal progress visualization
- Usage analytics and trends
- Top apps and categories breakdown
- Multi-device activity overview

## 🧪 Testing

Run tests (when implemented):
```bash
python test.py
```

## 📄 License

This project is provided as-is for educational and commercial use.

## 👤 Author

Digital Activity Flow System - Built as a comprehensive analytics solution

## 📞 Support

For issues or questions:
1. Check the troubleshooting section above
2. Verify database connectivity with `python db.py`
3. Check Flask application logs for detailed error messages
