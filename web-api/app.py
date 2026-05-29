from flask import Flask, request, jsonify
from flask_cors import CORS
from nba_api.stats.static import players
from nba_api.stats.endpoints import playercareerstats
import requests

app = Flask(__name__)
CORS(app) 

# --- ROUTE 1: Fast NBA Data ---
@app.route('/api/search')
def search():
    query = request.args.get('name', '').lower()
    
    nba_players = players.get_players()
    found_players = [p for p in nba_players if query in p['full_name'].lower()]
    
    if not found_players:
        return jsonify({"error": "Player not found"}), 404
        
    player = found_players[0]
    player_id = player['id']
    
    try:
        career = playercareerstats.PlayerCareerStats(player_id=player_id)
        stats_dict = career.get_dict()
        rows = stats_dict['resultSets'][0]['rowSet']
        headers = stats_dict['resultSets'][0]['headers']
        
        latest_season = rows[-1] 
        gp = latest_season[headers.index('GP')] 
        pts = round(latest_season[headers.index('PTS')] / gp, 1) if gp > 0 else 0
        reb = round(latest_season[headers.index('REB')] / gp, 1) if gp > 0 else 0
        ast = round(latest_season[headers.index('AST')] / gp, 1) if gp > 0 else 0

        payload = {
            "first_name": player['first_name'],
            "last_name": player['last_name'],
            "team": "NBA API Data", 
            "media": { "headshot_url": f"https://cdn.nba.com/headshots/nba/latest/1040x760/{player_id}.png" },
            "stats": { "pts": pts, "reb": reb, "ast": ast },
            "status": "ACTIVE" if player['is_active'] else "RETIRED"
        }
        return jsonify(payload)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- ROUTE 2: Asynchronous AI Generation ---
@app.route('/api/ai-scout', methods=['POST'])
def ai_scout():
    data = request.json
    # Build the prompt using the data sent from the frontend
    prompt = f"Act as an elite basketball scout. In 2 short sentences, pitch why a team should sign {data.get('name')}. Base it on these stats: {data.get('pts')} Points, {data.get('reb')} Rebounds, {data.get('ast')} Assists per game."
    
    try:
        ollama_response = requests.post('http://ollama:11434/api/generate', json={
            "model": "llama3.2:1b",
            "prompt": prompt,
            "stream": False
        }, timeout=60) # High timeout because CPU AI generation takes time!
        
        if ollama_response.status_code == 200:
            ai_pitch = ollama_response.json().get('response', '').strip()
            return jsonify({"pitch": ai_pitch})
        else:
            return jsonify({"pitch": "AI analysis failed."}), 500
    except Exception as e:
        return jsonify({"pitch": "AI Offline."}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)