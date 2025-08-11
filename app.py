from flask import Flask, render_template, request, jsonify, session, send_file
import chess
import chess.engine
import threading
import time
import json
import os
import uuid
from datetime import datetime
import tempfile
import logging
import subprocess

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-here')  # Use environment variable in production

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ChessGame:
    def __init__(self):
        self.board = chess.Board()
        self.engine_white = None
        self.engine_black = None
        self.engine_paths = [
            "stockfish.exe",  # System PATH
            "stockfish",      # Linux/Mac
            "/usr/local/bin/stockfish",  # Common install location
            "/usr/bin/stockfish",        # Package manager install
            "/opt/homebrew/bin/stockfish"  # Mac Homebrew
        ]
        self.engine_thinking = False
        self.engine_time_limit = 2.0
        self.engine_battle_active = False
        self.game_mode = "player_vs_engine"  # "player_vs_engine", "player_vs_player", "engine_vs_engine"
        self.engine_level = 15  # Stockfish skill level (0-20)
        self.move_history = []
        self.selected_square = None
        self.last_move = None
        self.engine_ready = False
        self.player_color = chess.WHITE  # Player plays as white by default
        self._lock = threading.Lock()
        
    def find_stockfish_path(self):
        """Find a working Stockfish executable path"""
        for path in self.engine_paths:
            try:
                # Check if the path exists and is executable
                if os.path.exists(path) and os.access(path, os.X_OK):
                    # Test if it's actually Stockfish
                    process = subprocess.Popen([path], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    process.stdin.write(b"uci\n")
                    process.stdin.flush()
                    output = process.stdout.readline()
                    process.terminate()
                    if b"Stockfish" in output or b"id name" in output:
                        logger.info(f"Found Stockfish at: {path}")
                        return path
            except Exception as e:
                logger.debug(f"Stockfish check failed for {path}: {e}")
                continue
        
        # Try to find stockfish in PATH
        try:
            import shutil
            stockfish_path = shutil.which("stockfish")
            if stockfish_path:
                logger.info(f"Found Stockfish in PATH: {stockfish_path}")
                return stockfish_path
        except Exception:
            pass
            
        logger.warning("Stockfish engine not found in any standard locations")
        return None
    
    def start_engines(self):
        """Initialize chess engines"""
        engine_path = self.find_stockfish_path()
        if not engine_path:
            logger.error("No Stockfish engine found")
            return False
            
        try:
            if not self.engine_white:
                self.engine_white = chess.engine.SimpleEngine.popen_uci(engine_path)
                logger.info("White engine initialized")
            if not self.engine_black:
                self.engine_black = chess.engine.SimpleEngine.popen_uci(engine_path)
                logger.info("Black engine initialized")
            
            # Configure engines
            try:
                self.engine_white.configure({"Skill Level": self.engine_level})
                self.engine_black.configure({"Skill Level": self.engine_level})
            except chess.engine.EngineError as e:
                logger.warning(f"Could not configure engine: {e}")
            
            self.engine_ready = True
            return True
        except Exception as e:
            logger.error(f"Engine initialization error: {e}")
            self.engine_ready = False
            return False
    
    def close_engines(self):
        """Close chess engines properly"""
        try:
            if self.engine_white:
                self.engine_white.quit()
                self.engine_white = None
            if self.engine_black:
                self.engine_black.quit()
                self.engine_black = None
            logger.info("Engines closed successfully")
        except Exception as e:
            logger.error(f"Error closing engines: {e}")
    
    def get_board_state(self):
        """Get current board state for frontend"""
        board_state = []
        # Iterate ranks from 7 to 0 (8th rank to 1st rank) for proper board display
        for rank in range(7, -1, -1):
            row = []
            for file in range(8):
                square = chess.square(file, rank)
                piece = self.board.piece_at(square)
                if piece:
                    row.append({
                        'piece': piece.symbol(),
                        'color': 'white' if piece.color == chess.WHITE else 'black'
                    })
                else:
                    row.append(None)
            board_state.append(row)
        
        return {
            'board': board_state,
            'turn': 'white' if self.board.turn == chess.WHITE else 'black',
            'move_history': self.move_history,
            'selected_square': self.selected_square,
            'last_move': self.last_move,
            'game_over': self.board.is_game_over(),
            'result': self.board.result() if self.board.is_game_over() else None,
            'engine_thinking': self.engine_thinking,
            'engine_battle_active': self.engine_battle_active,
            'engine_ready': self.engine_ready,
            'game_mode': self.game_mode,
            'fen': self.board.fen(),
            'player_color': 'white' if self.player_color == chess.WHITE else 'black'
        }
    
    def make_move(self, from_square, to_square, promotion=None):
        """Make a move on the board"""
        with self._lock:
            try:
                # Convert from [file, rank] format to chess square
                from_chess_square = chess.square(from_square[0], from_square[1])
                to_chess_square = chess.square(to_square[0], to_square[1])
                
                move = chess.Move(from_chess_square, to_chess_square, promotion=promotion)
                
                if move in self.board.legal_moves:
                    # Store the move in SAN notation before pushing
                    move_san = self.board.san(move)
                    self.board.push(move)
                    
                    self.last_move = {'from': from_square, 'to': to_square}
                    self.selected_square = None
                    
                    # Update move history with proper algebraic notation
                    move_count = len(self.board.move_stack)
                    if move_count % 2 == 1:  # White's move
                        move_number = (move_count + 1) // 2
                        self.move_history.append(f"{move_number}. {move_san}")
                    else:  # Black's move
                        if self.move_history:
                            self.move_history[-1] += f" {move_san}"
                        else:
                            move_number = move_count // 2
                            self.move_history.append(f"{move_number}... {move_san}")
                    
                    logger.info(f"Move made: {move_san} ({move.uci()})")
                    return True
                else:
                    logger.warning(f"Illegal move attempted: {move.uci()}")
            except Exception as e:
                logger.error(f"Move error: {e}")
            return False
    
    def should_engine_move(self):
        """Check if it's the engine's turn to move"""
        if self.game_mode == "player_vs_player":
            return False
        elif self.game_mode == "engine_vs_engine":
            return True
        elif self.game_mode == "player_vs_engine":
            # Engine moves when it's not the player's turn
            return self.board.turn != self.player_color
        return False
    
    def get_engine_move(self):
        """Get move from chess engine"""
        if self.engine_thinking or self.board.is_game_over() or not self.engine_ready:
            return False
        
        current_engine = self.engine_white if self.board.turn == chess.WHITE else self.engine_black
        if not current_engine:
            logger.error("Engine not available")
            return False
        
        try:
            self.engine_thinking = True
            logger.info(f"Engine is thinking for {'white' if self.board.turn == chess.WHITE else 'black'}...")
            
            # Configure engine settings
            try:
                current_engine.configure({
                    "Skill Level": self.engine_level,
                    "Hash": 64,  # Memory in MB
                    "Threads": 1
                })
            except chess.engine.EngineError as e:
                logger.warning(f"Could not configure engine: {e}")
            
            # Get engine move with time limit
            result = current_engine.play(
                self.board,
                chess.engine.Limit(time=self.engine_time_limit),
                info=chess.engine.INFO_SCORE | chess.engine.INFO_PV
            )
            
            if result.move and result.move in self.board.legal_moves:
                from_square = [chess.square_file(result.move.from_square), chess.square_rank(result.move.from_square)]
                to_square = [chess.square_file(result.move.to_square), chess.square_rank(result.move.to_square)]
                
                # Log engine evaluation if available
                if result.info.get('score'):
                    score = result.info['score'].relative
                    logger.info(f"Engine evaluation: {score}")
                
                success = self.make_move(from_square, to_square, result.move.promotion)
                if success:
                    logger.info(f"Engine move: {result.move.uci()}")
                return success
        except Exception as e:
            logger.error(f"Engine move error: {e}")
            return False
        finally:
            self.engine_thinking = False
    
    def new_game(self):
        """Start a new game"""
        with self._lock:
            self.board.reset()
            self.move_history = []
            self.selected_square = None
            self.last_move = None
            self.engine_battle_active = False
            self.engine_thinking = False
            
            # Reinitialize engines if they were closed
            if not self.engine_ready:
                self.start_engines()
            
            logger.info("New game started")
    
    def undo_move(self):
        """Undo the last move"""
        with self._lock:
            if len(self.board.move_stack) > 0:
                move = self.board.pop()
                
                # Remove from move history
                if self.move_history:
                    last_entry = self.move_history[-1]
                    if ' ' in last_entry and not last_entry.endswith('.'):
                        # This was a complete move (white + black), remove black's move
                        parts = last_entry.split(' ', 2)
                        if len(parts) >= 3:  # "1. e4 e5" format
                            self.move_history[-1] = ' '.join(parts[:-1])
                        else:
                            self.move_history.pop()
                    else:
                        # This was just white's move, remove entirely
                        self.move_history.pop()
                
                self.selected_square = None
                self.last_move = None
                logger.info(f"Move undone: {move.uci()}")
                return True
            return False

# Global games dictionary to store game sessions
games = {}
games_lock = threading.Lock()

def get_game():
    """Get or create a game session"""
    if 'game_id' not in session:
        session['game_id'] = str(uuid.uuid4())
    
    game_id = session['game_id']
    
    with games_lock:
        if game_id not in games:
            games[game_id] = ChessGame()
            # Try to start engines
            if games[game_id].start_engines():
                logger.info(f"New game session created with engines: {game_id}")
            else:
                logger.warning(f"New game session created without engines: {game_id}")
    
    return games[game_id]

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/game_state')
def game_state():
    """Get current game state"""
    try:
        game = get_game()
        return jsonify(game.get_board_state())
    except Exception as e:
        logger.error(f"Error getting game state: {e}")
        return jsonify({'error': 'Failed to get game state'}), 500

@app.route('/api/move', methods=['POST'])
def make_move():
    """Make a move"""
    try:
        game = get_game()
        data = request.get_json()
        
        from_square = data.get('from')
        to_square = data.get('to')
        promotion = data.get('promotion')
        
        if not from_square or not to_square:
            return jsonify({'success': False, 'error': 'Invalid move data'})
        
        if promotion:
            promotion = getattr(chess, promotion.upper(), None)
        
        success = game.make_move(from_square, to_square, promotion)
        
        response_data = {'success': success, 'game_state': game.get_board_state()}
        
        # Check if engine should move after this player move
        if success and game.should_engine_move() and not game.board.is_game_over():
            logger.info("Triggering engine move...")
            
            def engine_move_task():
                try:
                    time.sleep(0.2)  # Small delay for better UX
                    game.get_engine_move()
                except Exception as e:
                    logger.error(f"Engine move task error: {e}")
            
            # Start engine move in a separate thread
            threading.Thread(target=engine_move_task, daemon=True).start()
        
        return jsonify(response_data)
    except Exception as e:
        logger.error(f"Error making move: {e}")
        return jsonify({'success': False, 'error': 'Failed to make move'}), 500

@app.route('/api/select_square', methods=['POST'])
def select_square():
    """Select a square"""
    try:
        game = get_game()
        data = request.get_json()
        
        file = data.get('file')
        rank = data.get('rank')
        
        if file is None or rank is None:
            return jsonify({'success': False, 'error': 'Invalid square data'})
        
        if game.engine_thinking or (game.game_mode == "engine_vs_engine" and game.engine_battle_active):
            return jsonify({'success': False, 'error': 'Cannot select during engine thinking'})
        
        square = chess.square(file, rank)
        
        # In player vs engine mode, only allow selecting player's pieces
        if game.game_mode == "player_vs_engine":
            piece = game.board.piece_at(square)
            if piece and piece.color == game.player_color and game.board.turn == game.player_color:
                game.selected_square = [file, rank]
            else:
                game.selected_square = None
        else:
            # For other modes, check if there's a piece on the square and it's the current player's turn
            piece = game.board.piece_at(square)
            if piece and ((piece.color == chess.WHITE and game.board.turn == chess.WHITE) or 
                          (piece.color == chess.BLACK and game.board.turn == chess.BLACK)):
                game.selected_square = [file, rank]
            else:
                game.selected_square = None
        
        return jsonify({'success': True, 'game_state': game.get_board_state()})
    except Exception as e:
        logger.error(f"Error selecting square: {e}")
        return jsonify({'success': False, 'error': 'Failed to select square'}), 500

@app.route('/api/engine_move', methods=['POST'])
def engine_move():
    """Request engine move"""
    try:
        game = get_game()
        
        if not game.engine_ready:
            return jsonify({'success': False, 'error': 'Engine not ready'})
        
        if game.board.is_game_over():
            return jsonify({'success': False, 'error': 'Game is over'})
        
        def engine_move_task():
            game.get_engine_move()
        
        # Start engine move in a separate thread
        threading.Thread(target=engine_move_task, daemon=True).start()
        
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error requesting engine move: {e}")
        return jsonify({'success': False, 'error': 'Failed to request engine move'}), 500

@app.route('/api/new_game', methods=['POST'])
def new_game():
    """Start a new game"""
    try:
        game = get_game()
        game.new_game()
        return jsonify({'success': True, 'game_state': game.get_board_state()})
    except Exception as e:
        logger.error(f"Error starting new game: {e}")
        return jsonify({'success': False, 'error': 'Failed to start new game'}), 500

@app.route('/api/undo_move', methods=['POST'])
def undo_move():
    """Undo last move"""
    try:
        game = get_game()
        success = game.undo_move()
        return jsonify({'success': success, 'game_state': game.get_board_state()})
    except Exception as e:
        logger.error(f"Error undoing move: {e}")
        return jsonify({'success': False, 'error': 'Failed to undo move'}), 500

@app.route('/api/set_game_mode', methods=['POST'])
def set_game_mode():
    """Set game mode"""
    try:
        game = get_game()
        data = request.get_json()
        mode = data.get('mode', 'player_vs_engine')
        
        if mode not in ['player_vs_engine', 'player_vs_player', 'engine_vs_engine']:
            return jsonify({'success': False, 'error': 'Invalid game mode'})
        
        game.game_mode = mode
        game.engine_battle_active = False
        
        # Ensure engines are ready for engine modes
        if mode != 'player_vs_player' and not game.engine_ready:
            game.start_engines()
        
        logger.info(f"Game mode set to: {mode}")
        return jsonify({'success': True, 'game_state': game.get_board_state()})
    except Exception as e:
        logger.error(f"Error setting game mode: {e}")
        return jsonify({'success': False, 'error': 'Failed to set game mode'}), 500

@app.route('/api/set_engine_settings', methods=['POST'])
def set_engine_settings():
    """Set engine settings"""
    try:
        game = get_game()
        data = request.get_json()
        
        if 'time_limit' in data:
            time_limit = float(data['time_limit'])
            if 0.1 <= time_limit <= 60:  # Reasonable bounds
                game.engine_time_limit = time_limit
                logger.info(f"Engine time limit set to: {time_limit}")
        
        if 'level' in data:
            level = int(data['level'])
            if 0 <= level <= 20:  # Stockfish skill level range
                game.engine_level = level
                logger.info(f"Engine skill level set to: {level}")
                
                # Update engine configuration if engines are running
                if game.engine_white:
                    try:
                        game.engine_white.configure({"Skill Level": level})
                    except Exception as e:
                        logger.warning(f"Could not configure white engine: {e}")
                
                if game.engine_black:
                    try:
                        game.engine_black.configure({"Skill Level": level})
                    except Exception as e:
                        logger.warning(f"Could not configure black engine: {e}")
        
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error setting engine settings: {e}")
        return jsonify({'success': False, 'error': 'Failed to set engine settings'}), 500

@app.route('/api/toggle_engine_battle', methods=['POST'])
def toggle_engine_battle():
    """Toggle engine vs engine battle"""
    try:
        game = get_game()
        
        if not game.engine_ready:
            return jsonify({'success': False, 'error': 'Engines not ready'})
        
        if not game.engine_battle_active:
            if not (game.engine_white and game.engine_black):
                return jsonify({'success': False, 'error': 'Engines not initialized'})
            
            game.engine_battle_active = True
            game.game_mode = "engine_vs_engine"
            logger.info("Engine battle started")
            
            # Start battle
            def battle_thread():
                move_count = 0
                max_moves = 200  # Prevent infinite games
                
                while (game.engine_battle_active and 
                       not game.board.is_game_over() and 
                       move_count < max_moves):
                    
                    if not game.engine_thinking:
                        move_success = game.get_engine_move()
                        
                        if not move_success:
                            logger.warning("Engine move failed, stopping battle")
                            break
                        
                        move_count += 1
                        time.sleep(0.5)  # Delay between moves for visualization
                    else:
                        time.sleep(0.1)
                
                game.engine_battle_active = False
                logger.info("Engine battle ended")
            
            threading.Thread(target=battle_thread, daemon=True).start()
        else:
            game.engine_battle_active = False
            logger.info("Engine battle stopped")
        
        return jsonify({'success': True, 'game_state': game.get_board_state()})
    except Exception as e:
        logger.error(f"Error toggling engine battle: {e}")
        return jsonify({'success': False, 'error': 'Failed to toggle engine battle'}), 500

@app.route('/api/save_game')
def save_game():
    """Save current game in PGN format"""
    try:
        game = get_game()
        
        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.pgn', delete=False)
        
        # Write PGN headers
        temp_file.write('[Event "Flask Chess Game"]\n')
        temp_file.write(f'[Date "{datetime.now().strftime("%Y.%m.%d")}"]\n')
        temp_file.write('[White "Player/Engine"]\n')
        temp_file.write('[Black "Player/Engine"]\n')
        temp_file.write(f'[Result "{game.board.result()}"]\n')
        temp_file.write(f'[FEN "{chess.STARTING_FEN}"]\n')
        temp_file.write('\n')
        
        # Write moves in UCI format for easy loading
        for move in game.board.move_stack:
            temp_file.write(f"{move.uci()}\n")
        
        temp_file.write(f"\n{game.board.result()}\n")
        temp_file.close()
        
        return send_file(
            temp_file.name,
            as_attachment=True,
            download_name=f"chess_game_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pgn",
            mimetype='application/x-chess-pgn'
        )
    except Exception as e:
        logger.error(f"Error saving game: {e}")
        return jsonify({'success': False, 'error': 'Failed to save game'}), 500

@app.route('/api/load_game', methods=['POST'])
def load_game():
    """Load a game from uploaded file"""
    try:
        game = get_game()
        
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file uploaded'})
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'})
        
        # Read file content
        content = file.read().decode('utf-8')
        lines = [line.strip() for line in content.split('\n') if line.strip()]
        
        # Filter out PGN headers and result
        moves = []
        for line in lines:
            if not line.startswith('[') and not line in ['1-0', '0-1', '1/2-1/2', '*']:
                # Handle both UCI format and potential PGN move format
                if len(line) >= 4 and not '.' in line[:3]:  # Looks like UCI
                    moves.append(line)
        
        # Reset board and replay moves
        game.new_game()
        
        for move_uci in moves:
            try:
                move = chess.Move.from_uci(move_uci)
                if move in game.board.legal_moves:
                    from_square = [chess.square_file(move.from_square), chess.square_rank(move.from_square)]
                    to_square = [chess.square_file(move.to_square), chess.square_rank(move.to_square)]
                    game.make_move(from_square, to_square, move.promotion)
                else:
                    return jsonify({'success': False, 'error': f'Illegal move: {move_uci}'})
            except Exception as e:
                logger.error(f"Error parsing move {move_uci}: {e}")
                return jsonify({'success': False, 'error': f'Invalid move format: {move_uci}'})
        
        logger.info(f"Game loaded successfully with {len(moves)} moves")
        return jsonify({'success': True, 'game_state': game.get_board_state()})
        
    except Exception as e:
        logger.error(f"Error loading game: {e}")
        return jsonify({'success': False, 'error': f'Failed to load game: {str(e)}'})

@app.route('/api/get_fen')
def get_fen():
    """Get current position in FEN notation"""
    try:
        game = get_game()
        return jsonify({'fen': game.board.fen()})
    except Exception as e:
        logger.error(f"Error getting FEN: {e}")
        return jsonify({'success': False, 'error': 'Failed to get FEN'}), 500

@app.route('/api/set_position', methods=['POST'])
def set_position():
    """Set position from FEN"""
    try:
        game = get_game()
        data = request.get_json()
        fen = data.get('fen')
        
        if not fen:
            return jsonify({'success': False, 'error': 'No FEN provided'})
        
        # Validate and set FEN
        test_board = chess.Board()
        test_board.set_fen(fen)  # This will raise an exception if FEN is invalid
        
        game.board.set_fen(fen)
        game.move_history = []  # Clear move history for new position
        game.selected_square = None
        game.last_move = None
        
        logger.info(f"Position set from FEN: {fen}")
        return jsonify({'success': True, 'game_state': game.get_board_state()})
        
    except Exception as e:
        logger.error(f"Error setting position: {e}")
        return jsonify({'success': False, 'error': f'Invalid FEN: {str(e)}'})

@app.teardown_appcontext
def cleanup_game(error):
    """Clean up resources when app context tears down"""
    if error:
        logger.error(f"App context error: {error}")

def initialize_app():
    """Initialize application"""
    logger.info("Flask Chess Application starting...")

if __name__ == '__main__':
    try:
        initialize_app()
        logger.info("Starting Flask Chess server...")
        app.run(debug=True, host='0.0.0.0', port=5000, threaded=True)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        # Close all game engines
        with games_lock:
            for game in games.values():
                game.close_engines()
    except Exception as e:
        logger.error(f"Server error: {e}")
        raise