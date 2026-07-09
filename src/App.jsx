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
  const [theme, setTheme] = useState(() => (localStorage.getItem('music-agent-theme') || 'dark'));
  const [mode, setMode] = useState('arrange');
  const [status, setStatus] = useState('就绪');
  const [loading, setLoading] = useState(false);
  const [toast, setToast] = useState(null);
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
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('music-agent-theme', theme);
  }, [theme]);

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
      if (field === 'role') {
        if (val === 'vocal' && !updated.voice) updated.voice = '冰糖';
        if (val === 'instrument') updated.voice = '';
      }
      return updated;
    }));
  };

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
      showToast(`人声生成完成（${d.vocal_segments || 0} 段）`, 'success');
      setStatus('人声生成完成，正在生成编曲规划...');
      const r2 = await fetch(API + '/api/arrange', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ job_id: jobId })
      });
      if (!r2.ok) { const e = await r2.json(); throw new Error(e.detail); }
      const d2 = await r2.json();
      setArrangement(d2.arrangement);
      setStep('plan-confirm');
      setStatus('编曲规划已生成，请确认');
      showToast('编曲规划已生成', 'success');
    } catch (e) {
      setStatus('出错: ' + e.message);
      showToast(e.message, 'error');
    } finally {
      setLoading(false);
    }
  }, [confirmedLyrics, jobId, tracks, showToast]);

  const handleConfirmPlan = useCallback(async () => {
    setLoading(true);
    setStatus('正在生成音符...');
    try {
      const r = await fetch(API + '/api/notes', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ job_id: jobId })
      });
      if (!r.ok) { const e = await r.json(); throw new Error(e.detail); }
      const d = await r.json();
      setNotesArrangement(d.arrangement);
      setStep('notes-confirm');
      setStatus('音符已生成，请确认');
      showToast('音符已生成', 'success');
    } catch (e) {
      setStatus('出错: ' + e.message);
      showToast(e.message, 'error');
    } finally {
      setLoading(false);
    }
  }, [jobId, showToast]);

  const handleConfirmNotes = useCallback(async () => {
    setLoading(true);
    setStep('generating');
    setStatus('正在渲染音频...');
    try {
      const r = await fetch(API + '/api/render', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ job_id: jobId })
      });
      if (!r.ok) { const e = await r.json(); throw new Error(e.detail); }
      const d = await r.json();
      setRenderedTracks(d.tracks || []);
      setMasterUrl(d.master_url || null);
      setMultitrackUrl(d.multitrack_url || null);
      setStep('done');
      setStatus('渲染完成');
      showToast('渲染完成！', 'success');
    } catch (e) {
      setStatus('出错: ' + e.message);
      showToast(e.message, 'error');
      setStep('notes-confirm');
    } finally {
      setLoading(false);
    }
  }, [jobId, showToast]);

  const handleReset = useCallback(() => {
    setStep('input');
    setJobId(null);
    setLyricsData(null);
    setConfirmedLyrics('');
    setStyle('');
    setArrangement(null);
    setTracks(DEFAULT_TRACKS);
    setRenderedTracks([]);
    setMasterUrl(null);
    setMultitrackUrl(null);
    setSelectedTrack(null);
    setReferences(null);
    setNotesArrangement(null);
    setStatus('就绪');
  }, []);

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
          <button className="theme-toggle" onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')} title={theme === 'dark' ? '切换到日间模式' : '切换到夜间模式'}>
            {theme === 'dark' ? '☀️' : '🌙'}
          </button>
        </div>
      </header>
      {!hasKey && (
        <div style={{ background: 'var(--error-bg)', border: '1px solid var(--error)', borderRadius: 'var(--radius)', padding: '10px 16px', margin: '0 16px', display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 18 }}>⚠️</span>
          <span style={{ color: 'var(--error)', fontSize: 13, fontWeight: 600 }}>未配置 API Key</span>
          <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>请在左侧面板填入小米 MiMo API Key 后点击「保存配置」，否则无法生成歌词、编曲和人声。</span>
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
                  jobId={jobId}
                />
              )}
              {masterUrl && <MasterPlayer masterUrl={masterUrl} multitrackUrl={multitrackUrl} arrangement={arrangement} tracks={renderedTracks} jobId={jobId} />}
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