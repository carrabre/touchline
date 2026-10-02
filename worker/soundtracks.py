"""Licensed instrumental pool; pin a random choice to each render revision."""
import hashlib, json, pathlib, secrets

TRACK_DIR = pathlib.Path(__file__).parent / 'tracks'
TRACKS = json.loads((TRACK_DIR / 'catalog.json').read_text())

def credits(track):
 return (f"'{track['title']}' by {track['artist']} — released under CC-BY 4.0. "
         f"www.scottbuckley.com.au\n{track['source']}\n{track['licenseUrl']}\n"
         "Music trimmed, looped, faded and mixed with match audio.\n"
         "Include these credits in the description when sharing the reel.\n")

def select_music(match):
 revision = match.get('revision', 0)
 existing = match.get('renderMusic')
 if existing and existing.get('revision') == revision:
  track = next((t for t in TRACKS if t['id'] == existing['id']), None)
  if track is None: raise RuntimeError('Saved soundtrack is unavailable.')
 else:
  requested = match.get('music', 'random')
  if requested == 'random':
   pool = [t for t in TRACKS if not existing or t['id'] != existing['id']]
   track = secrets.choice(pool or TRACKS)
  else:
   track = next((t for t in TRACKS if t['id'] == requested), None)
   if track is None: raise RuntimeError('Unknown soundtrack selection.')
  match['renderMusic'] = {**track, 'revision': revision, 'credits': credits(track)}
 path = TRACK_DIR / track['file']
 if hashlib.sha256(path.read_bytes()).hexdigest() != track['sha256']:
  raise RuntimeError('Soundtrack failed integrity validation.')
 return track, path

def mix_music(cut, directory, match, duration, run):
 track, music = select_music(match)
 final = directory / 'reel.mp4'
 fade = max(0, duration - 2)
 # Normalize each song first; retain field audio and duck music beneath speech.
 graph = (f'[0:a]volume=1,asplit=2[game][side];'
          f'[1:a]loudnorm=I=-16:TP=-2:LRA=11,volume=0.32,'
          f'afade=t=in:d=1,afade=t=out:st={fade}:d=2[music];'
          '[music][side]sidechaincompress=threshold=0.04:ratio=6:attack=20:release=300[duck];'
          '[game][duck]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95[a]')
 run(['ffmpeg','-nostdin','-v','error','-i',str(cut),'-stream_loop','-1','-ss',str(track['start']),
      '-i',str(music),'-filter_complex',graph,'-map','0:v:0','-map','[a]',
      '-c:v','copy','-c:a','aac','-b:a','192k','-ar','48000','-t',str(duration),
      '-metadata','comment='+credits(track),'-movflags','+faststart','-y',str(final)],300)
 (directory / 'music-credits.txt').write_text(credits(track))
 return final
