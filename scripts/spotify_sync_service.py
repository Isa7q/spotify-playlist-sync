#!/usr/bin/env python3
import os
import re
import json
import sqlite3
import requests
import traceback
from http.server import BaseHTTPRequestHandler, HTTPServer

# Configurações de Caminhos
lidarr_db_path = "/app/volumes/lidarr/config/lidarr.db"
music_dir = "/midias/data/media/music"

# Dicionário de mapeamento de artistas para variações em japonês/romaji/alternativos
# Permite cruzar nomes em inglês/japonês na biblioteca local
artist_mappings = {
    "Kenshi Yonezu": ["Kenshi Yonezu", "米津玄師"],
    "Hikaru Utada": ["Hikaru Utada", "宇多田ヒカル"],
    "Ado": ["Ado"],
    "YOASOBI": ["YOASOBI", "Ayase", "几田りら", "ikura"],
    "QUEEN BEE": ["QUEEN BEE", "Queen Bee", "女王蜂"],
    "THREEE": ["THREEE", "すりぃ"],
    "shytaupe": ["shytaupe", "シャイトープ"],
    "noa": ["noa"],
    "PAS TASTA": ["PAS TASTA"],
    "Mrs. GREEN APPLE": ["Mrs. GREEN APPLE", "Mrs.GREEN APPLE"],
    "milet": ["milet"],
    "CHANMINA": ["CHANMINA", "ちゃんみな"],
    "Yorushika": ["Yorushika", "ヨルシカ"],
    "MAISONdes": ["MAISONdes"],
    "Ling tosite sigure": ["Ling tosite sigure", "凛として時雨"],
    "Atarayo": ["Atarayo", "あたらよ"],
    "花耶": ["花耶", "Hanaya"],
    "TOMOO": ["TOMOO"],
    "Bialystocks": ["Bialystocks"],
    "AiNA THE END": ["AiNA THE END", "アイナ・ジ・エンド"],
    "natori": ["natori", "なとり"],
    "Tatsuya Kitani": ["Tatsuya Kitani", "キタニタツヤ"],
    "jo0ji": ["jo0ji"],
    "SPYAIR": ["SPYAIR"],
    "UNISON SQUARE GARDEN": ["UNISON SQUARE GARDEN"],
    "ryo (supercell)": ["ryo (supercell)", "ryo", "supercell"],
    "Shiyui": ["Shiyui", "シユイ"],
    "Yurina Hirate": ["Yurina Hirate", "平手友梨奈"],
    "AKASAKI": ["AKASAKI"],
    "ASH DA HERO": ["ASH DA HERO"],
    "Kochi コチ": ["Kochi コチ", "Kochi", "コチ"],
    "yonige": ["yonige"],
    "上伊那ぼたん（CV.鈴代紗弓）": ["上伊那ぼたん", "上伊那ぼたん（CV.鈴代紗弓）", "Kamina Botan"],
    "KANA-BOON": ["KANA-BOON"],
    "ASIAN KUNG-FU GENERATION": ["ASIAN KUNG-FU GENERATION"],
    "宮川愛李": ["宮川愛李", "宮川愛微", "Miyakawa Airi"],
    "RLOEVO": ["RLOEVO"],
    "osage": ["osage"],
    "ミーマイナー": ["ミーマイナー", "Mei Minor"],
    "asmi": ["asmi"],
    "yama": ["yama"],
    "ZUTOMAYO": ["ZUTOMAYO", "Zutomayo", "ずっと真夜中でいいのに。", "ずっと真夜中でいいのに"],
    "Lilas": ["Lilas", "Lilas Ikuta", "幾田りら", "ikura"],
    "羊文学": ["羊文学", "Hitsujibungaku", "Hitsuji Bungaku"],
    "水曜日のカンパネラ": ["水曜日のカンパネラ", "WEDNESDAY CAMPANELLA", "Wednesday Campanella"],
    "こっちのけんと": ["こっちのけんと", "Kocchi no Kento", "Kocchino Kento"],
    "ナナヲアカリ": ["ナナヲアカリ", "NANAOAKARI", "Nanao Akari"],
    "GReeeeN": ["GReeeeN", "GRe4N BOYZ"],
    "GRe4N BOYZ": ["GRe4N BOYZ", "GReeeeN"],
    "大槻マキ": ["大槻マキ", "Maki Otsuki"],
    "きただにひろし": ["きただにひろし", "Hiroshi Kitadani"]
}

# Dicionário de mapeamento de títulos para variações japonês/inglês/romaji/alternativos
# Evita problemas se a música for salva no HD com grafia em romaji mas no Spotify estiver em japonês
title_mappings = {
    "アドレナ": ["アドレナ", "Adorena", "Adorena - YOASOBI"],
    "言って。": ["言って。", "言って", "Itte", "Itte."],
    "ハク": ["ハク", "Haku"],
    "ソナーレ": ["ソナーレ", "Sonare"],
    "Sonare": ["Sonare", "ソナーレ"],
    "セレナーデ": ["セレナーデ", "Serenade"],
    "よあけのうた - Yoake no uta": ["よあけのうた", "Yoake no uta", "Yoake no uta - jo0ji"],
    "かすかなはな - Kasuka na Hana (OP Theme to Hell's Paradise: Jigokuraku Season 2)": ["かすかなはな", "Kasuka na Hana", "Kasuka na Hana - Tatsuya Kitani", "Kasuka na Hana - Tatsuya Kitani, BABYMETAL"],
    "ルミナス - Luminous": ["ルミナス", "Luminous"],
    "言伝": ["言伝", "Kotodate", "Kotozute"],
    "シャケナベイベー": ["シャケナベイベー", "Shakena Baby", "Shake na Baby"],
    "感情グラス": ["感情グラス", "Kanjo Glass", "Kanjou Glass"],
    "部屋とガラクタと私": ["部屋とガラクタと私", "Heya to Garakuta to Watashi"],
    "あわ": ["あわ", "Awa"],
    "飛ぼうよ": ["飛ぼうよ", "Tobouyo"],
    "リーチライト": ["リーチライト", "Reach Light", "Reachlight"],
    "Kill or Kiss": ["Kill or Kiss", "Kill or Kiss - Yurina Hirate"]
}

def normalize(text):
    if not text:
        return ""
    text = text.lower()
    text = text.replace("&#x27;", "'").replace("&amp;", "&")
    # Limpa caracteres especiais comuns de busca, mantém letras, números e ideogramas
    text = re.sub(r'[\s\-_,\.\(\)\[\]!\?"\']+', ' ', text)
    return text.strip()

# Limpar prefixo de faixa do nome do arquivo
def clean_filename(filename):
    name, _ = os.path.splitext(filename)
    name = name.strip()
    # Remove prefixos numéricos como "01. ", "01 - ", "1-01 ", "01 ", "A1. ", "CD1-01 "
    name = re.sub(r'^(?:(?:CD|dis[ck]\s*)\d+[\s\-_]*)?\d+[\s\-_,\.]*', '', name, flags=re.IGNORECASE)
    return name.strip()

def get_artist_variations(artists_list):
    variations = set()
    for art in artists_list:
        art_clean = art.replace('\xa0', ' ').strip()
        variations.add(art_clean)
        if art_clean in artist_mappings:
            for v in artist_mappings[art_clean]:
                variations.add(v)
        main_art = art_clean.split('（')[0].split('(')[0]
        variations.add(main_art)
    return [v.lower() for v in variations]

def get_title_variations(title):
    variations = set()
    variations.add(title)
    if title in title_mappings:
        for v in title_mappings[title]:
            variations.add(v)
    
    # Extrai o título principal limpando strings extras em parênteses ou hifens
    title_main = title.split(' - ')[0].split(' (')[0].split(' -')[0]
    variations.add(title_main)
    if title_main in title_mappings:
        for v in title_mappings[title_main]:
            variations.add(v)
            
    return [normalize(v) for v in variations]

def index_local_music(music_dir):
    audio_extensions = ('.mp3', '.flac', '.m4a', '.ogg', '.wav', '.opus')
    audio_files = []
    for root, dirs, files in os.walk(music_dir):
        for f in files:
            if f.lower().endswith(audio_extensions):
                full_path = os.path.join(root, f)
                rel_path = os.path.relpath(full_path, music_dir)
                audio_files.append((rel_path, f))
    return audio_files

def find_local_match(title, artists, all_audio_files):
    title_vars = get_title_variations(title)
    artist_vars = get_artist_variations(artists)
    
    candidates = []
    
    for rel_path, filename in all_audio_files:
        path_lower = rel_path.lower()
        file_lower = filename.lower()
        
        # 1. O artista deve estar no caminho da pasta
        artist_in_path = any(art_var in path_lower for art_var in artist_vars)
        if not artist_in_path:
            continue
            
        file_clean = clean_filename(file_lower)
        file_clean_norm = normalize(file_clean)
        
        # 2. O título da faixa deve ser compatível
        match_found = False
        matched_var = None
        for t_var in title_vars:
            if t_var in file_clean_norm:
                match_found = True
                matched_var = t_var
                break
                
        if match_found:
            score = 100
            
            # Se for uma correspondência exata
            if file_clean_norm == matched_var:
                score += 50
                
            # Penaliza versões instrumentais indesejadas
            spotify_is_inst = any("instrumental" in v or "inst" in v or "off vocal" in v or "karaoke" in v for v in title_vars)
            file_is_inst = "instrumental" in file_clean_norm or "inst" in file_clean_norm or "off vocal" in file_clean_norm or "karaoke" in file_clean_norm
            if file_is_inst and not spotify_is_inst:
                score -= 80
                
            # Penaliza versões TV Size indesejadas
            spotify_is_tv = any("tv size" in v or "tv-size" in v or "tv version" in v for v in title_vars)
            file_is_tv = "tv size" in file_clean_norm or "tv-size" in file_clean_norm or "tv version" in file_clean_norm
            if file_is_tv and not spotify_is_tv:
                score -= 40
                
            # Penaliza remixes indesejados
            spotify_is_remix = any("remix" in v or "mix" in v for v in title_vars)
            file_is_remix = "remix" in file_clean_norm or ("mix" in file_clean_norm and "mix" not in matched_var)
            if file_is_remix and not spotify_is_remix:
                score -= 30
                
            # Bônus por proximidade de tamanho de string
            size_diff = abs(len(file_clean_norm) - len(matched_var))
            if size_diff < 2:
                score += 20
            elif size_diff < 5:
                score += 10
                
            candidates.append((score, rel_path))
            
    if candidates:
        candidates.sort(key=lambda x: x[0], reverse=True)
        return candidates[0][1]
        
    return None

def run_synchronization():
    if not os.path.exists(lidarr_db_path):
        return {"error": f"Banco de dados do Lidarr não encontrado em {lidarr_db_path}"}

    conn = sqlite3.connect(lidarr_db_path)
    cursor = conn.cursor()
    
    # 1. Buscar todas as playlists monitoradas da lista SpotifyPlaylist
    cursor.execute("SELECT Settings FROM ImportLists WHERE Implementation='SpotifyPlaylist'")
    rows_playlists = cursor.fetchall()
    if not rows_playlists:
        conn.close()
        return {"error": "Import list 'SpotifyPlaylist' não encontrada no Lidarr."}
        
    playlist_settings = json.loads(rows_playlists[0][0])
    playlist_ids = playlist_settings.get("playlistIds", [])
    if not playlist_ids:
        conn.close()
        return {"error": "Nenhuma playlist monitorada configurada na lista do Lidarr."}
        
    # 2. Coletar todos os refreshTokens do Spotify no banco do Lidarr
    cursor.execute("SELECT Name, Settings FROM ImportLists WHERE Implementation LIKE 'Spotify%'")
    rows_all = cursor.fetchall()
    
    refresh_tokens = []
    for r_name, settings_str in rows_all:
        try:
            sett = json.loads(settings_str)
            ref_t = sett.get("refreshToken")
            if ref_t:
                refresh_tokens.append((r_name, ref_t))
        except Exception:
            continue
            
    if not refresh_tokens:
        conn.close()
        return {"error": "Nenhum refreshToken do Spotify encontrado no Lidarr."}
        
    # 3. Tentar renovar e validar contra a API do Spotify (fallback automático)
    access_token = None
    headers = None
    renew_url = "https://spotify.lidarr.audio/renew"
    
    for r_name, ref_t in refresh_tokens:
        try:
            r = requests.get(renew_url, params={"refresh_token": ref_t}, timeout=15)
            if r.status_code != 200:
                continue
            token_data = r.json()
            tok = token_data.get("access_token")
            if not tok:
                continue
                
            # Valida o token contra a API do Spotify lendo a primeira playlist cadastrada
            test_headers = {"Authorization": f"Bearer {tok}"}
            test_url = f"https://api.spotify.com/v1/playlists/{playlist_ids[0]}"
            r_test = requests.get(test_url, headers=test_headers, timeout=10)
            
            if r_test.status_code == 200:
                access_token = tok
                headers = test_headers
                print(f"✓ Token de acesso renovado e validado com sucesso usando a conta de '{r_name}'!")
                break
            else:
                print(f"⚠ Token de acesso gerado por '{r_name}' deu erro 401 no Spotify. Tentando próximo...")
        except Exception as e:
            print(f"Erro ao testar token de '{r_name}': {e}")
            continue
            
    if not access_token:
        conn.close()
        return {"error": "Todos os refreshTokens do Spotify no Lidarr falharam na validação com o Spotify."}

    all_audio_files = index_local_music(music_dir)
    results = []
    
    for playlist_id in playlist_ids:
        playlist_url = f"https://api.spotify.com/v1/playlists/{playlist_id}"
        try:
            r = requests.get(playlist_url, headers=headers, timeout=15)
            if r.status_code != 200:
                results.append({"playlist_id": playlist_id, "status": "error", "message": f"Erro HTTP {r.status_code}"})
                continue
            playlist_data = r.json()
            
            # Garantir nome padrão em caso de string nula ou vazia
            playlist_name = playlist_data.get("name")
            if not playlist_name or playlist_name.strip() == "":
                playlist_name = f"Spotify-{playlist_id}"
                
            safe_playlist_name = re.sub(r'[\/:*?"<>|]', '', playlist_name).strip()
            # Garante que não contenha pontos/parênteses sozinhos
            safe_playlist_name = safe_playlist_name.strip(" .()")
            if not safe_playlist_name:
                safe_playlist_name = f"Spotify-{playlist_id}"
                
            playlist_file = f"{safe_playlist_name}.m3u"
            playlist_path = os.path.join(music_dir, playlist_file)
        except Exception as e:
            results.append({"playlist_id": playlist_id, "status": "error", "message": str(e)})
            continue

        tracks = []
        tracks_url = f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks?limit=100"
        
        while tracks_url:
            try:
                r = requests.get(tracks_url, headers=headers, timeout=15)
                if r.status_code != 200:
                    break
                page_data = r.json()
                for item in page_data.get("items", []):
                    track = item.get("track")
                    if not track:
                        continue
                    title = track.get("name")
                    artists = [a.get("name") for a in track.get("artists", []) if a.get("name")]
                    tracks.append({"title": title, "artists": artists})
                tracks_url = page_data.get("next")
            except Exception as e:
                break
                
        m3u_lines = ["#EXTM3U\n"]
        matched_count = 0
        
        for track in tracks:
            title = track["title"]
            artists = track["artists"]
            artists_str = ", ".join(artists)
            
            local_path = find_local_match(title, artists, all_audio_files)
            if local_path:
                m3u_lines.append(f"#EXTINF:-1,{artists_str} - {title}\n")
                m3u_lines.append(f"{local_path}\n")
                matched_count += 1
            else:
                m3u_lines.append(f"# MÚSICA AUSENTE (Baixando via Lidarr): {artists_str} - {title}\n")
                
        try:
            with open(playlist_path, "w", encoding="utf-8") as f:
                f.writelines(m3u_lines)
            results.append({
                "playlist_name": playlist_name,
                "playlist_id": playlist_id,
                "status": "success",
                "tracks_total": len(tracks),
                "tracks_matched": matched_count
            })
        except Exception as e:
            results.append({"playlist_id": playlist_id, "status": "error", "message": f"Erro ao gravar M3U: {e}"})
            
    conn.close()
    return {"status": "success", "results": results}


class SincronizadorHTTPHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_POST(self):
        if self.path == '/sync':
            try:
                print("Iniciando sincronização via requisição HTTP do Navidrome...")
                output = run_synchronization()
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(output, ensure_ascii=False).encode('utf-8'))
                print("Sincronização concluída e resposta enviada.")
            except Exception as e:
                err_msg = {"status": "error", "message": str(e), "trace": traceback.format_exc()}
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(err_msg).encode('utf-8'))
                print(f"Erro na execução da sincronização HTTP: {e}")
        else:
            self.send_response(404)
            self.end_headers()

def run_server():
    server_address = ('0.0.0.0', 8090)
    httpd = HTTPServer(server_address, SincronizadorHTTPHandler)
    print("Serviço Sidecar do Sincronizador iniciado na porta 8090...")
    httpd.serve_forever()

if __name__ == "__main__":
    run_server()
