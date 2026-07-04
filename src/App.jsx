import { useState, useCallback, useEffect } from 'react';
import ConfigPanel from './components/ConfigPanel';
import ArrangePanel from './components/ArrangePanel';
import VoicePanel from './components/VoicePanel';
import TrackList from './components/TrackList';
import MasterPlayer from './components/MasterPlayer';
import './App.css';

const API = '';
const DEFAULT_TRACKS = [
  { id: 'vocal_1', name: '人声主唱', role: 'vocal', instrument: 'piano', voice: '冰糖', part: 'melody', channel: 0 },
  { id: 'inst_1', name: '伴奏乐器', role: 'instrument', instrument: 'guitar', voice: '', part: 'accompaniment', channel: 1 },
];

function App() {
  const [mode, setMode] = useState('arrange');
  const [status, setStatus] = useState('就绪');
  const [loading, setLoading] = useState(false);
  const [toast, setToast] = useState(null);
  // Flow: input -> lyrics-voice (pick voice) -> generating-vocal -> plan-confirm -> notes-confirm -> generating -> done
  const [step, setStep] = useState('input');
  const [jobId, setJobId] = useState(null);
  const [lyricsData, setLyricsData] = useState(null);
  const [confirmedLyrics, setConfirmedLyrics] = useState('');
  const [style, setStyle] = useState('');
  const [arrangement, setArrangement] = useState(null);
  const [tracks, setTracks] = useState(DEFAULT_TRACKS);
  const [renderedTracks, setRenderedTracks] = useState([]);
  const [masterUrl, setMasterUrl] = useState(null);
  const [multitrackUrl, setMultitrackUrl] = useState(null);
  const [selectedTrack, setSelectedTrack] = useState(null);
  const [voiceMode, setVoiceMode] = useState('synth');
  const [references, setReferences] = useState(null);
  const [notesArrangement, setNotesArrangement] = useState(null);
  const [hasKey, setHasKey] = useState(false);

  useEffect(() => {
    fetch(API + '/api/config').then(r => r.json()).then(d => {
      setHasKey(!!d.api_key && d.api_key !== '');
    }).catch(() => {});
  }, []);

  const showToast = useCallback((msg, type = 'info') => {
    setToast({ msg, type }); setTimeout(() => setToast(null), 3500);
  }, []);

  const addTrack = () => {
    const idx = tracks.length;
    const isVocal = idx % 2 === 0;
    setTracks(prev => [...prev, {
      id: 'track_' + (idx + 1),
      name: isVocal ? '人声 ' + (Math.floor(idx / 2) + 1) : '乐器 ' + (Math.ceil(idx / 2)),
      role: isVocal ? 'vocal' : 'instrument',
      instrument: 'piano',
      voice: isVocal ? '冰糖' : '',
      part: isVocal ? 'melody' : 'accompaniment',
      channel: idx
    }]);
  };

  const removeTrack = (tid) => {
    if (tracks.length > 1) setTracks(prev => prev.filter(t => t.id !== tid));
    else showToast('至少保留一个音轨', 'error');
  };

  const updateTrack = (tid, field, val) => {
    setTracks(prev => prev.map(t => {
      if (t.id !== tid) return t;
      const updated = { ...t, [field]: val };
      // Auto-switch voice when role changes
      if (field === 'role') {
        if (val === 'vocal' && !updated.voice) updated.voice = '冰糖';
        if (val === 'instrument') updated.voice = '';
      }
      return updated;
    }));
  };

  // Step 1: Generate lyrics
  const handleGenerateLyrics = useCallback(async (prompt, styleVal) => {
    setLoading(true);
    setStyle(styleVal || '');
    setStatus('正在生成歌词...');
    try {
      const r = await fetch(API + '/api/lyrics', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt, style: styleVal })
      });
      if (!r.ok) { const e = await r.json(); throw new Error(e.detail); }
      const d = await r.json();
      setJobId(d.job_id);
      setLyricsData(d.lyrics);
      setConfirmedLyrics(d.lyrics.full_lyrics || '');
      setReferences(d.references || null);
      setStep('lyrics-voice');
      setStatus('歌词已生成，请选择演唱音色');
      showToast('歌词已生成，请选择音色', 'success');
    } catch (e) {
      setStatus('出错: ' + e.message);
      showToast(e.message, 'error');
    } finally {
      setLoading(false);
    }
  }, [showToast]);

  // Step 2: Confirm lyrics + voice -> generate vocal TTS
  const handleConfirmLyrics = useCallback(async () => {
    if (!confirmedLyrics.trim()) {
      showToast('歌词不能为空', 'error');
      return;
    }
    setLoading(true);
    setStatus('正在生成人声演唱（TTS）...');
    try {
      const r = await fetch(API + '/api/vocal', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          job_id: jobId,
          lyrics: confirmedLyrics,
          voice: tracks.find(t => t.role === 'vocal')?.voice || '冰糖'
        })
      });
      if (!r.ok) { const e = await r.json(); throw new Error(e.detail); }
      const d = await r.json();
      showToast(`人声生成完成（${d.vocal.duration_sec.toFixed(1)}秒）`, 'success');
      setStatus('人声完成，正在设计编曲...');
      // Now auto-generate plan based on vocal duration
      const rp = await fetch(API + '/api/plan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          job_id: jobId,
          lyrics: confirmedLyrics,
          style,
          tracks,
          bpm: undefined,
          time_signature: undefined,
          key: undefined
        })
      });
      if (!rp.ok) { const e = await rp.json(); throw new Error(e.detail); }
      const pd = await rp.json();
      setArrangement(pd.arrangement);
      setReferences(pd.references || references);
      setStep('plan-confirm');
      setStatus('编曲规划完成');
      showToast('规划完成', 'success');
    } catch (e) {
      setStatus('出错: ' + e.message);
      showToast(e.message, 'error');
    } finally {
      setLoading(false);
    }
  }, [jobId, confirmedLyrics, style, tracks, references, showToast]);

  // Step 3: Confirm plan -> generate notes
  const handleConfirmPlan = useCallback(async () => {
    setLoading(true);
    setStatus('生成音符中...');
    try {
      const n = await fetch(API + '/api/notes', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ job_id: jobId, lyrics: confirmedLyrics, style })
      });
      if (!n.ok) { const e = await n.json(); throw new Error(e.detail); }
      const nd = await n.json();
      setNotesArrangement(nd.arrangement);
      setStep('notes-confirm');
      setStatus('音符生成完成');
      showToast('音符生成完成', 'success');
    } catch (e) {
      setStatus('出错: ' + e.message);
      showToast(e.message, 'error');
    } finally {
      setLoading(false);
    }
  }, [jobId, confirmedLyrics, style, showToast]);

  // Step 4: Confirm notes -> render
  const handleConfirmNotes = useCallback(async () => {
    setLoading(true);
    setStep('generating');
    setStatus('渲染乐器轨道 + 混音...');
    try {
      const rr = await fetch(API + '/api/render/' + jobId, { method: 'POST' });
      if (!rr.ok) { const e = await rr.json(); throw new Error(e.detail); }
      const rd = await rr.json();
      setRenderedTracks(rd.tracks);
      setMasterUrl(rd.master_url);
      setMultitrackUrl(rd.multitrack_url || null);
      setArrangement(rd.arrangement);
      setStep('done');
      setStatus('完成');
      showToast('编曲完成，共 ' + rd.tracks.length + ' 条音轨', 'success');
    } catch (e) {
      setStatus('出错: ' + e.message);
      showToast(e.message, 'error');
      setStep('notes-confirm');
    } finally {
      setLoading(false);
    }
  }, [jobId, showToast]);

  const handleReset = () => {
    setStep('input');
    setJobId(null);
    setLyricsData(null);
    setConfirmedLyrics('');
    setArrangement(null);
    setNotesArrangement(null);
    setRenderedTracks([]);
    setMasterUrl(null);
    setMultitrackUrl(null);
    setReferences(null);
    setStatus('就绪');
  };

  const handleSynth = useCallback(async (text, voice, synthStyle) => {
    setLoading(true);
    setStatus('合成中...');
    try {
      const r = await fetch(API + '/api/synth', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, voice, style: synthStyle || '' })
      });
      if (!r.ok) { const e = await r.json(); throw new Error(e.detail); }
      const d = await r.json();
      setStatus('完成');
      showToast('合成完成', 'success');
      return d.audio_url;
    } catch (e) {
      setStatus('出错');
      showToast(e.message, 'error');
      return null;
    } finally {
      setLoading(false);
    }
  }, [showToast]);

  const handleClone = useCallback(async (text, file) => {
    setLoading(true);
    setStatus('克隆中...');
    try {
      const fd = new FormData();
      fd.append('text', text);
      fd.append('file', file);
      const r = await fetch(API + '/api/clone', { method: 'POST', body: fd });
      if (!r.ok) { const e = await r.json(); throw new Error(e.detail); }
      const d = await r.json();
      setStatus('完成');
      showToast('克隆完成', 'success');
      return d.audio_url;
    } catch (e) {
      setStatus('出错');
      showToast(e.message, 'error');
      return null;
    } finally {
      setLoading(false);
    }
  }, [showToast]);

  const handleVolumeChange = useCallback((tid, vol) => {
    setRenderedTracks(prev => prev.map(t => t.id === tid ? { ...t, volume: vol } : t));
  }, []);

  return (
    <div className="app">
      <header className="header">
        <h1>Music Agent - AI 编曲工作站</h1>
        <div className="header-actions">
          <div className="mode-tabs">
            <button className={'mode-tab ' + (mode === 'arrange' ? 'active' : '')} onClick={() => setMode('arrange')}>编曲模式</button>
            <button className={'mode-tab ' + (mode === 'voice' ? 'active' : '')} onClick={() => setMode('voice')}>语音模式</button>
          </div>
        </div>
      </header>
      {!hasKey && (
        <div style={{ background: '#f8514930', border: '1px solid #f85149', borderRadius: 8, padding: '10px 16px', margin: '0 16px', display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 18 }}>⚠️</span>
          <span style={{ color: '#f85149', fontSize: 13, fontWeight: 600 }}>未配置 API Key</span>
          <span style={{ color: '#8b949e', fontSize: 12 }}>请在左侧面板填入小米 MiMo API Key 后点击「保存配置」，否则无法生成歌词、编曲和人声。</span>
        </div>
      )}
      <div className="main-layout">
        <aside className="sidebar">
          <ConfigPanel showToast={showToast} hasKey={hasKey} setHasKey={setHasKey} />
        </aside>
        <main className="center-panel">
          {mode === 'arrange' ? (
            <>
              <ArrangePanel
                step={step}
                loading={loading}
                style={style}
                setStyle={setStyle}
                lyricsData={lyricsData}
                confirmedLyrics={confirmedLyrics}
                setConfirmedLyrics={setConfirmedLyrics}
                arrangement={arrangement}
                notesArrangement={notesArrangement}
                tracks={tracks}
                references={references}
                onGenerateLyrics={handleGenerateLyrics}
                onConfirmLyrics={handleConfirmLyrics}
                onConfirmPlan={handleConfirmPlan}
                // removed: vocal-confirm merged into lyrics-confirm
                onConfirmNotes={handleConfirmNotes}
                onReset={handleReset}
                onAddTrack={addTrack}
                onRemoveTrack={removeTrack}
                onUpdateTrack={updateTrack}
              />
              {renderedTracks.length > 0 && (
                <TrackList
                  tracks={renderedTracks}
                  selectedTrack={selectedTrack}
                  onSelect={setSelectedTrack}
                  onVolumeChange={handleVolumeChange}
                />
              )}
              {masterUrl && <MasterPlayer masterUrl={masterUrl} multitrackUrl={multitrackUrl} arrangement={arrangement} tracks={renderedTracks} />}
            </>
          ) : (
            <VoicePanel
              voiceMode={voiceMode}
              setVoiceMode={setVoiceMode}
              onSynth={handleSynth}
              onClone={handleClone}
              loading={loading}
            />
          )}
        </main>
      </div>
      <div className="status-bar">
        {loading && <div className="spinner" />}
        <span>{status}</span>
      </div>
      {toast && <div className={'toast ' + toast.type}>{toast.msg}</div>}
    </div>
  );
}

export default App;






