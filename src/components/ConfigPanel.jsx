import { useState, useEffect } from 'react';

const API = '';

export default function ConfigPanel({ showToast, hasKey, setHasKey }) {
  const [presets, setPresets] = useState([]);
  const [baseUrl, setBaseUrl] = useState('https://api.xiaomimimo.com');
  const [apiKey, setApiKey] = useState('');
  const [providerFormat, setProviderFormat] = useState('openai');
  const [model, setModel] = useState('mimo-v2.5-pro');
  const [ttsModel, setTtsModel] = useState('mimo-v2.5-tts');
  const [showKey, setShowKey] = useState(false);
  const [skills, setSkills] = useState([]);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    fetch(`${API}/api/presets`).then(r => r.json()).then(d => setPresets(d.presets || []));
    fetch(`${API}/api/config`).then(r => r.json()).then(d => {
      if (d.base_url) setBaseUrl(d.base_url);
      if (d.provider_format) setProviderFormat(d.provider_format);
      if (d.model) setModel(d.model);
      if (d.tts_model) setTtsModel(d.tts_model);
      if (d.api_key) { setApiKey(d.api_key); setSaved(true); if (setHasKey) setHasKey(true); }
    });
    fetch(`${API}/api/skills`).then(r => r.json()).then(d => setSkills(d.skills || [])).catch(() => {});
  }, []);

  const applyPreset = (preset) => {
    setBaseUrl(preset.base_url);
    setProviderFormat(preset.provider_format);
    if (preset.model) setModel(preset.model);
    if (preset.tts_model) setTtsModel(preset.tts_model);
    showToast(`已应用：${preset.name}`, 'info');
  };

  const saveConfig = async () => {
    if (!apiKey.trim()) {
      showToast('请先填入 API Key', 'error');
      return;
    }
    try {
      const resp = await fetch(`${API}/api/config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          base_url: baseUrl,
          api_key: apiKey,
          provider_format: providerFormat,
          model,
          tts_model: ttsModel
        }),
      });
      if (resp.ok) {
        setSaved(true);
        if (setHasKey) setHasKey(true);
        showToast('配置已保存。此 Key 将用于编曲（LLM）和人声合成（TTS）', 'success');
      } else {
        showToast('保存失败', 'error');
      }
    } catch (e) {
      showToast('保存失败: ' + e.message, 'error');
    }
  };

  return (
    <>
      <div className="sidebar-section">
        <h3>🔑 API 配置（统一密钥）</h3>
        <p style={{ fontSize: 11, color: 'var(--text-muted)', margin: '0 0 12px', lineHeight: 1.5 }}>
          一个 API Key 同时用于 <span style={{ color: 'var(--info)' }}>编曲规划（LLM）</span> 和{' '}
          <span style={{ color: '#f778ba' }}>人声合成（TTS）</span>，以及{' '}
          <span style={{ color: 'var(--success)' }}>声音克隆</span>。
        </p>
        <div className="config-field">
          <label>预置方案</label>
          <select onChange={e => {
            const i = parseInt(e.target.value);
            if (i >= 0 && presets[i]) applyPreset(presets[i]);
          }}>
            <option value={-1}>-- 选择预置 --</option>
            {presets.map((p, i) => <option key={i} value={i}>{p.name}</option>)}
          </select>
        </div>
        <div className="config-field">
          <label>API URL</label>
          <input type="text" value={baseUrl} onChange={e => setBaseUrl(e.target.value)}
            placeholder="https://api.xiaomimimo.com" />
        </div>
        <div className="config-field">
          <label>API Key</label>
          <div style={{ display: 'flex', gap: 4 }}>
            <input type={showKey ? 'text' : 'password'} value={apiKey}
              onChange={e => { setApiKey(e.target.value); setSaved(false); }}
              placeholder="sk-..."
              style={{ flex: 1 }} />
            <button className="btn btn-small" onClick={() => setShowKey(!showKey)}
              style={{ minWidth: 36 }}>{showKey ? '隐藏' : '显示'}</button>
          </div>
          {saved && apiKey && (
            <div style={{ fontSize: 11, color: 'var(--success)', marginTop: 4 }}>✓ 已保存</div>
          )}
        </div>
        <div className="config-field">
          <label>协议格式</label>
          <select value={providerFormat} onChange={e => setProviderFormat(e.target.value)}>
            <option value="openai">OpenAI 兼容</option>
            <option value="anthropic">Anthropic 兼容</option>
          </select>
        </div>
        <div className="config-field">
          <label>编曲模型（LLM）</label>
          <select value={model} onChange={e => setModel(e.target.value)}>
            <option value="mimo-v2.5-pro">mimo-v2.5-pro（推理旗舰）</option>
            <option value="mimo-v2.5">mimo-v2.5（全模态）</option>
            <option value="mimo-v2.5-pro-ultraspeed">mimo-v2.5-pro-ultraspeed</option>
            <option value="mimo-v2-flash">mimo-v2-flash（轻量）</option>
          </select>
        </div>
        <div className="config-field">
          <label>TTS 模型（人声合成/克隆）</label>
          <select value={ttsModel} onChange={e => setTtsModel(e.target.value)}>
            <option value="mimo-v2.5-tts">mimo-v2.5-tts</option>
            <option value="mimo-v2.5-tts-voiceclone">mimo-v2.5-tts-voiceclone</option>
            <option value="mimo-v2.5-tts-voicedesign">mimo-v2.5-tts-voicedesign</option>
          </select>
        </div>
        <button className="btn btn-primary" onClick={saveConfig} style={{ width: '100%' }}>
          保存配置
        </button>
      </div>

      <div className="sidebar-section">
        <h3>便携插件</h3>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 8 }}>
          {skills.map(s => (
            <div key={s.id} style={{ background: 'var(--bg-input)', border: '1px solid #30363d', borderRadius: 6, padding: '8px 10px' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-primary)' }}>{s.name}</div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>{s.type} · v{s.version}</div>
              {s.metadata?.description && (
                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>{s.metadata.description}</div>
              )}
              <div style={{ fontSize: 11, color: 'var(--info)', marginTop: 6 }}>
                {s.runtime?.engine || ''}
                {s.runtime?.python ? ` ${s.runtime.python}` : ''}
                {s.license ? ` · ${s.license}` : ''}
              </div>
            </div>
          ))}
          {!skills.length && <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>未发现插件</span>}
        </div>
      </div>

      <div className="sidebar-section">
        <h3>关于</h3>
        <div style={{ fontSize: 12, color: 'var(--text-muted)', lineHeight: 1.5 }}>
          <p>基于小米 MiMo 大模型的 AI 编曲工作站</p>
          <p>平台：<a href="https://platform.xiaomimimo.com" target="_blank" rel="noreferrer" style={{ color: 'var(--info)' }}>platform.xiaomimimo.com</a></p>
          <p>文档：<a href="https://mimo.mi.com/docs" target="_blank" rel="noreferrer" style={{ color: 'var(--info)' }}>mimo.mi.com/docs</a></p>
          <p style={{ fontSize: 11, color: 'var(--text-muted)' }}>
            Token Plan: 国内 <code style={{ color: 'var(--info)', fontSize: 10 }}>token-plan-cn.xiaomimimo.com</code><br/>
            新加坡 <code style={{ color: 'var(--info)', fontSize: 10 }}>token-plan-sg.xiaomimimo.com</code>
          </p>
        </div>
      </div>
    </>
  );
}


