# Flask Chess GUI

A feature-rich web-based chess application built with Flask and JavaScript that supports human vs human, human vs engine, and engine vs engine gameplay with a modern, responsive interface.

## Features

- **Multiple Game Modes**:
  - Player vs Engine (human plays as White, engine as Black)
  - Player vs Player (local multiplayer)
  - Engine vs Engine (automated battles with real-time visualization)

- **Advanced Gameplay**:
  - Full chess rule validation using python-chess library
  - Move history with algebraic notation
  - Visual move highlighting and last move indication
  - Square selection with hover effects
  - Undo functionality
  - Game over detection (checkmate, stalemate, draws)

- **Engine Integration**:
  - Stockfish chess engine support with automatic path detection
  - Configurable engine strength (1-20 skill levels)
  - Adjustable thinking time (0.1-60 seconds per move)
  - Real-time engine thinking indicators
  - Threaded engine calculations for responsive gameplay

- **Web Interface**:
  - Modern responsive design with gradient backgrounds
  - Unicode chess pieces with enhanced styling and shadows
  - Coordinate labels (a-h, 1-8)
  - Smooth animations and hover effects
  - Game over modal notifications
  - Session-based game state management

- **Game Management**:
  - Save games in PGN format
  - Load games from PGN/text files
  - Export current position as FEN notation
  - Set custom positions via FEN input

## Requirements

- Python 3.7 or higher
- Required Python packages (install via `pip install -r requirements.txt`)
- Stockfish chess engine
- Modern web browser with JavaScript enabled

## Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/top-site/chess3
   cd chess3
   ```

2. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Install Stockfish chess engine**:
   
   **Windows:**
   ```bash
   # Download from https://stockfishchess.org/download/
   # Or using chocolatey:
   choco install stockfish
   ```
   
   **macOS:**
   ```bash
   # Using Homebrew:
   brew install stockfish
   ```
   
   **Linux (Ubuntu/Debian):**
   ```bash
   sudo apt-get update
   sudo apt-get install stockfish
   ```
   
   **Linux (CentOS/RHEL):**
   ```bash
   sudo yum install stockfish
   # or
   sudo dnf install stockfish
   ```

4. **Optional - Environment Configuration**:
   Create a `.env` file for production settings:
   ```bash
   SECRET_KEY=your-super-secret-key-here
   FLASK_ENV=production
   ```

## Usage

Run the application:
```bash
python app.py
```

The web interface will be available at `http://localhost:5000`

### Game Controls

- **Click** pieces to select them (highlighted in blue)
- **Click** destination squares to make moves
- **New Game**: Start a fresh game
- **Undo Move**: Take back the last move
- **Save Game**: Download move history as PGN file
- **Load Game**: Upload and replay a saved PGN/text file
- **Start Engine Battle**: Watch engines play against each other automatically

### Game Modes

1. **Player vs Engine**: Human controls pieces, engine responds automatically
2. **Player vs Player**: Two humans take turns on the same browser
3. **Engine vs Engine**: Automated battle with real-time move progression

### Engine Settings

- **Time Limit**: Set engine thinking time (0.1-60 seconds)
- **Engine Strength**: Adjust skill level (1-20, where 20 is strongest)
- **Game Mode**: Switch between different play modes instantly

## File Structure

```
flask-chess-gui/
├── app.py                 # Main Flask application with game logic
├── templates/
│   └── index.html        # Web interface with CSS and JavaScript
├── requirements.txt      # Python dependencies
├── README.md            # This documentation
└── .gitignore          # Git ignore file
```

## API Endpoints

The application provides RESTful API endpoints for all chess operations:

- `GET /api/game_state` - Get current board state and game information
- `POST /api/move` - Make a chess move with from/to coordinates
- `POST /api/select_square` - Select a square on the board
- `POST /api/engine_move` - Request engine to calculate and make a move
- `POST /api/new_game` - Start a new game
- `POST /api/undo_move` - Undo the last move
- `POST /api/set_game_mode` - Change game mode
- `POST /api/set_engine_settings` - Update engine configuration
- `POST /api/toggle_engine_battle` - Start/stop automated engine battles
- `GET /api/save_game` - Download current game as PGN file
- `POST /api/load_game` - Upload and load PGN file
- `GET /api/get_fen` - Get current position in FEN notation
- `POST /api/set_position` - Set board position from FEN string

## Saved Game Format

Games are saved in standard PGN format:
```
[Event "Flask Chess Game"]
[Date "2024.01.15"]
[White "Player/Engine"]
[Black "Player/Engine"]
[Result "1-0"]

e2e4
e7e5
g1f3
b8c6
...

1-0
```

## Troubleshooting

### Stockfish Not Found
- The application automatically searches common installation paths
- Check console logs for specific error messages about engine detection
- Ensure Stockfish is installed and accessible in your system PATH
- On Windows, verify `stockfish.exe` is properly installed

### Engine Not Responding
- Check that Stockfish process isn't hanging in task manager
- Try reducing engine thinking time for faster responses
- Restart the Flask application to reinitialize engines
- Verify engine executable has proper permissions

### Web Interface Issues
- Ensure JavaScript is enabled in your browser
- Try refreshing the page if board doesn't load
- Check browser console for JavaScript errors
- Modern browsers required (Chrome 80+, Firefox 75+, Safari 13+)

### Performance Issues
- Reduce engine thinking time for faster gameplay
- Lower engine skill level for quicker calculations
- Close other resource-intensive applications
- Use single-threaded mode if experiencing threading issues

## Technical Details

- **Backend Framework**: Flask with session-based game management
- **Chess Logic**: python-chess library for move validation and game rules
- **Engine Communication**: UCI protocol with threaded calculations
- **Frontend**: Vanilla JavaScript with CSS animations
- **Threading**: Non-blocking engine moves with proper synchronization
- **File Handling**: PGN format support for game import/export
- **Session Management**: UUID-based game sessions with cleanup

## Configuration

### Automatic Stockfish Detection
The application searches for Stockfish in these locations:
- System PATH
- `stockfish.exe` (Windows)
- `/usr/local/bin/stockfish`
- `/usr/bin/stockfish` 
- `/opt/homebrew/bin/stockfish` (macOS Homebrew)

### Engine Settings
- **Skill Level**: 1-20 (1 = beginner, 20 = master strength)
- **Hash Memory**: 64MB (configurable in code)
- **Threads**: 1 (configurable in code)
- **Time Control**: 0.1-60 seconds per move

## Contributing

Feel free to submit issues and pull requests. Some areas for improvement:
- Opening book integration
- Advanced position analysis features
- Network multiplayer capabilities
- Mobile-responsive design enhancements
- Tournament management system
- Database integration for game storage

## License

This project is open source. Please check the license file for details.

---

**Note**: This application requires Stockfish chess engine installation for AI gameplay. The web interface handles all game logic and visualization, while Stockfish provides move calculations and position evaluation.
