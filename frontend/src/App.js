import React, { useState, useEffect } from 'react';
import axios from 'axios';

const API = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';

// ... (keep OTPModal unchanged)
function OTPModal({ phone, onClose, onSuccess }) {
  const [otp, setOtp] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const verify = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await axios.post(`${API}/auth/verify-otp`, { phone, otp });
      if (res.data.status === 'SUCCESS') {
        onSuccess();
      } else {
        setError(res.data.message || 'OTP ভুল হয়েছে');
      }
    } catch { setError('Verification failed'); }
    setLoading(false);
  };

  return (
    <div className="modal-overlay">
      <div className="modal">
        <h3>📱 OTP Verification</h3>
        <p>{phone} নম্বরে OTP পাঠানো হয়েছে</p>
        {error && <div className="alert alert-error">⚠️ {error}</div>}
        <div className="form-group">
          <label>OTP Code</label>
          <input placeholder="e.g. 12345" value={otp} onChange={e => setOtp(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && verify()} />
        </div>
        <div className="modal-actions">
          <button className="btn btn-primary" onClick={verify} disabled={loading}>
            {loading ? '⏳ Verifying...' : '✅ Verify'}
          </button>
          <button className="btn" style={{background:'rgba(255,255,255,0.05)',color:'#9ca3af'}} onClick={onClose}>Cancel</button>
        </div>
      </div>
    </div>
  );
}

// ... (keep AccountsTab unchanged)
function AccountsTab() {
  const [accounts, setAccounts] = useState([]);
  const [form, setForm] = useState({ phone: '', proxy_ip: '', proxy_port: '', proxy_user: '', proxy_pass: '' });
  const [otpPhone, setOtpPhone] = useState(null);
  const [msg, setMsg] = useState({ type: '', text: '' });
  const [loading, setLoading] = useState(false);

  const fetchAccounts = () => axios.get(`${API}/accounts`).then(r => setAccounts(r.data));
  useEffect(() => { fetchAccounts(); }, []);

  const showMsg = (type, text) => { setMsg({ type, text }); setTimeout(() => setMsg({ type: '', text: '' }), 3000); };

  const addAccount = async () => {
    if (!form.phone) return showMsg('error', 'Phone number দিন');
    setLoading(true);
    try {
      await axios.post(`${API}/accounts`, { ...form, proxy_port: parseInt(form.proxy_port) || null });
      showMsg('success', 'Account যোগ হয়েছে!');
      setForm({ phone: '', proxy_ip: '', proxy_port: '', proxy_user: '', proxy_pass: '' });
      fetchAccounts();
    } catch (e) { showMsg('error', e.response?.data?.detail || 'Error'); }
    setLoading(false);
  };

  const deleteAccount = async (id) => {
    if (!window.confirm('Delete করবেন?')) return;
    await axios.delete(`${API}/accounts/${id}`);
    fetchAccounts();
  };

  const toggleStatus = async (id, current) => {
    const newStatus = current === 'Active' ? 'Banned' : 'Active';
    await axios.patch(`${API}/accounts/${id}/status`, { status: newStatus });
    fetchAccounts();
  };

  const sendOtp = async (phone) => {
    try {
      const res = await axios.post(`${API}/auth/send-otp`, { phone });
      if (res.data.status === 'OTP_SENT') setOtpPhone(phone);
      else if (res.data.status === 'AUTHORIZED') showMsg('success', 'Already logged in!');
      else showMsg('error', res.data.status);
    } catch { showMsg('error', 'OTP পাঠাতে ব্যর্থ'); }
  };

  const f = (k, v) => setForm(p => ({ ...p, [k]: v }));

  return (
    <div>
      <div className="section-header">
        <div>
          <h2>👤 Accounts</h2>
          <p>Telegram accounts manage করুন</p>
        </div>
      </div>

      {msg.text && <div className={`alert alert-${msg.type}`}>{msg.text}</div>}

      <div className="card">
        <div className="card-title">➕ New Account</div>
        <div className="form-grid">
          <div className="form-group">
            <label>Phone Number</label>
            <input placeholder="+8801XXXXXXXXX" value={form.phone} onChange={e => f('phone', e.target.value)} />
          </div>
          <div className="form-group">
            <label>Proxy IP</label>
            <input placeholder="31.59.20.176" value={form.proxy_ip} onChange={e => f('proxy_ip', e.target.value)} />
          </div>
          <div className="form-group">
            <label>Proxy Port</label>
            <input placeholder="6754" value={form.proxy_port} onChange={e => f('proxy_port', e.target.value)} />
          </div>
          <div className="form-group">
            <label>Proxy User</label>
            <input placeholder="username" value={form.proxy_user} onChange={e => f('proxy_user', e.target.value)} />
          </div>
          <div className="form-group">
            <label>Proxy Pass</label>
            <input placeholder="password" type="password" value={form.proxy_pass} onChange={e => f('proxy_pass', e.target.value)} />
          </div>
        </div>
        <button className="btn btn-primary" onClick={addAccount} disabled={loading}>
          {loading ? '⏳ Adding...' : '➕ Add Account'}
        </button>
      </div>

      <div className="table-wrapper">
        {accounts.length === 0 ? (
          <div className="empty-state"><div className="empty-icon">📭</div><p>কোনো account নেই</p></div>
        ) : (
          <table>
            <thead><tr><th>Phone</th><th>Proxy IP</th><th>Status</th><th>Actions</th></tr></thead>
            <tbody>
              {accounts.map(acc => (
                <tr key={acc.id}>
                  <td>{acc.phone}</td>
                  <td style={{color:'#6b7280'}}>{acc.proxy_ip || '—'}</td>
                  <td>
                    <span className={`badge badge-${acc.status === 'Active' ? 'active' : 'banned'}`}>
                      <span className="badge-dot"></span>{acc.status}
                    </span>
                  </td>
                  <td>
                    <div className="action-row">
                      <button className="btn btn-sm" style={{background:'rgba(245,158,11,0.1)',color:'#f59e0b',border:'1px solid rgba(245,158,11,0.3)'}}
                        onClick={() => sendOtp(acc.phone)}>📱 OTP Login</button>
                      <button className={`btn btn-sm ${acc.status === 'Active' ? 'btn-danger' : 'btn-success'}`}
                        onClick={() => toggleStatus(acc.id, acc.status)}>
                        {acc.status === 'Active' ? '🚫 Ban' : '✅ Activate'}
                      </button>
                      <button className="btn btn-sm btn-danger" onClick={() => deleteAccount(acc.id)}>🗑 Delete</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {otpPhone && (
        <OTPModal phone={otpPhone} onClose={() => setOtpPhone(null)}
          onSuccess={() => { setOtpPhone(null); showMsg('success', 'Login সফল হয়েছে!'); }} />
      )}
    </div>
  );
}

// ... (keep GroupsTab unchanged)
function GroupsTab() {
  const [groups, setGroups] = useState([]);
  const [form, setForm] = useState({ 
    name: '', username: '', content: '',
    max_messages_per_day: 50, start_hour: 9, end_hour: 21, 
    cooldown_minutes: 30, batch_size: 5,
    min_delay: 40, max_delay: 80
  });
  const [editing, setEditing] = useState(null);
  const [procUrl, setProcUrl] = useState('');
  const [procFile, setProcFile] = useState(null);
  const [newGroupUrl, setNewGroupUrl] = useState('');
  const [newGroupFile, setNewGroupFile] = useState(null);
  const [processing, setProcessing] = useState(false);
  const [msg, setMsg] = useState({ type: '', text: '' });

  const fetchGroups = () => axios.get(`${API}/groups`).then(r => setGroups(r.data));
  useEffect(() => { fetchGroups(); }, []);

  const showMsg = (type, text) => { setMsg({ type, text }); setTimeout(() => setMsg({ type: '', text: '' }), 3000); };

  const addGroup = async () => {
    if (!form.name || !form.username) return showMsg('error', 'Name এবং Username দিন');
    setProcessing(true);
    try {
      const res = await axios.post(`${API}/groups`, form);
      const groupId = res.data.id;
      
      // If file or URL is provided for new group, process it
      if (newGroupUrl || newGroupFile) {
        showMsg('success', 'Group তৈরি হয়েছে! এখন কন্টেন্ট অ্যানালাইসিস চলছে...');
        const formData = new FormData();
        if (newGroupUrl) formData.append('url', newGroupUrl);
        if (newGroupFile) formData.append('file', newGroupFile);
        await axios.post(`${API}/groups/${groupId}/process-content`, formData, {
          headers: { 'Content-Type': 'multipart/form-data' }
        });
        showMsg('success', 'Group তৈরি এবং কন্টেন্ট অ্যানালাইসিস সফল হয়েছে!');
      } else {
        showMsg('success', 'Group যোগ হয়েছে!');
      }
      
      setForm({ 
        name: '', username: '', content: '',
        max_messages_per_day: 50, start_hour: 9, end_hour: 21, 
        cooldown_minutes: 30, batch_size: 5,
        min_delay: 40, max_delay: 80
      });
      setNewGroupUrl('');
      setNewGroupFile(null);
      fetchGroups();
    } catch (e) { showMsg('error', e.response?.data?.detail || 'Error'); }
    setProcessing(false);
  };

  const updateGroup = async (id) => {
    await axios.patch(`${API}/groups/${id}`, { 
      content: editing.content, 
      name: editing.name,
      max_messages_per_day: parseInt(editing.max_messages_per_day),
      start_hour: parseInt(editing.start_hour),
      end_hour: parseInt(editing.end_hour),
      cooldown_minutes: parseInt(editing.cooldown_minutes),
      batch_size: parseInt(editing.batch_size),
      min_delay: parseInt(editing.min_delay),
      max_delay: parseInt(editing.max_delay)
    });
    showMsg('success', 'Group আপডেট হয়েছে!');
    setEditing(null);
    fetchGroups();
  };

  const processContent = async () => {
    if (!procUrl && !procFile) return showMsg('error', 'File অথবা URL দিন');
    setProcessing(true);
    const formData = new FormData();
    if (procUrl) formData.append('url', procUrl);
    if (procFile) formData.append('file', procFile);

    try {
      const res = await axios.post(`${API}/groups/${editing.id}/process-content`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 180000
      });
      if (res.data.status === 'SUCCESS') {
        showMsg('success', `✅ Content update হয়েছে! (${res.data.length} characters)`);
        setProcUrl('');
        setProcFile(null);
        const updated = await axios.get(`${API}/groups`);
        const current = updated.data.find(g => g.id === editing.id);
        if (current) setEditing(current);
        fetchGroups();
      } else {
        showMsg('error', 'Content update হয়নি');
      }
    } catch (e) {
      const detail = e.response?.data?.detail || e.message || 'Analysis failed';
      if (detail === 'No content provided') {
        showMsg('error', '⚠️ PDF থেকে text extract হয়নি। Image-based PDF হতে পারে। Text manually লিখুন।');
      } else {
        showMsg('error', detail);
      }
    } finally {
      setProcessing(false);
    }
  };

  const deleteGroup = async (id) => {
    if (!window.confirm('Delete করবেন?')) return;
    await axios.delete(`${API}/groups/${id}`);
    fetchGroups();
  };

  const f = (k, v) => setForm(p => ({ ...p, [k]: v }));

  return (
    <div>
      <div className="section-header">
        <div><h2>💬 Groups</h2><p>Target Telegram groups manage করুন</p></div>
      </div>

      {msg.text && <div className={`alert alert-${msg.type}`}>{msg.text}</div>}

      <div className="card">
        <div className="card-title">➕ New Group</div>
        <div className="form-grid">
          <div className="form-group">
            <label>Display Name</label>
            <input placeholder="Alpha Network" value={form.name} onChange={e => f('name', e.target.value)} />
          </div>
          <div className="form-group">
            <label>Group Username</label>
            <input placeholder="alphanetwork" value={form.username} onChange={e => f('username', e.target.value)} />
          </div>
        </div>
        
        <div className="form-grid" style={{gridTemplateColumns:'repeat(auto-fit, minmax(140px, 1fr))', marginBottom:'16px'}}>
          <div className="form-group">
            <label>Max Msg/Day</label>
            <input type="number" value={form.max_messages_per_day} onChange={e => f('max_messages_per_day', e.target.value)} />
          </div>
          <div className="form-group">
            <label>Hours (Start-End)</label>
            <div style={{display:'flex', gap:'4px', alignItems:'center'}}>
              <input type="number" style={{padding:'4px'}} value={form.start_hour} onChange={e => f('start_hour', e.target.value)} />
              <span>-</span>
              <input type="number" style={{padding:'4px'}} value={form.end_hour} onChange={e => f('end_hour', e.target.value)} />
            </div>
          </div>
          <div className="form-group">
            <label>Batch Size</label>
            <input type="number" value={form.batch_size} onChange={e => f('batch_size', e.target.value)} />
          </div>
          <div className="form-group">
            <label>Cooldown (Min)</label>
            <input type="number" value={form.cooldown_minutes} onChange={e => f('cooldown_minutes', e.target.value)} />
          </div>
          <div className="form-group">
            <label>Delay (Min-Max s)</label>
            <div style={{display:'flex', gap:'4px', alignItems:'center'}}>
              <input type="number" style={{padding:'4px'}} value={form.min_delay} onChange={e => f('min_delay', e.target.value)} />
              <input type="number" style={{padding:'4px'}} value={form.max_delay} onChange={e => f('max_delay', e.target.value)} />
            </div>
          </div>
        </div>
        <div className="form-group" style={{marginBottom:'12px'}}>
          <label>AI Context / Information (Initial)</label>
          <textarea placeholder="এই group-এ কী কী বিষয়ে কথা বলবে তা এখানে লিখুন..." value={form.content} onChange={e => f('content', e.target.value)} />
        </div>
        
        <div className="form-group" style={{background:'rgba(167,139,250,0.05)',padding:'12px',borderRadius:'8px',marginBottom:'12px',border:'1px dashed rgba(167,139,250,0.2)'}}>
          <label style={{color:'#a78bfa',fontWeight:600,fontSize:'13px'}}>🧠 Context Processor (Optional)</label>
          <div className="form-grid" style={{marginTop:'8px',gap:'12px'}}>
            <div className="form-group">
              <label style={{fontSize:'11px'}}>Analyze Website URL</label>
              <input style={{height:'32px',fontSize:'12px'}} placeholder="https://..." value={newGroupUrl} onChange={e => setNewGroupUrl(e.target.value)} />
            </div>
            <div className="form-group">
              <label style={{fontSize:'11px'}}>Analyze Document</label>
              <input type="file" accept=".pdf,.docx,.txt" style={{fontSize:'11px'}} onChange={e => setNewGroupFile(e.target.files[0])} />
            </div>
          </div>
        </div>
        
        <button className="btn btn-primary" onClick={addGroup} disabled={processing}>
          {processing ? '⏳ Adding & Analyzing...' : '➕ Add Group'}
        </button>
      </div>

      <div className="table-wrapper">
        {groups.length === 0 ? (
          <div className="empty-state"><div className="empty-icon">💬</div><p>কোনো group নেই</p></div>
        ) : (
          <table>
            <thead><tr><th>Name</th><th>Username</th><th>Limits & Stats</th><th>Hours</th><th>Status</th><th>Actions</th></tr></thead>
            <tbody>
              {groups.map(grp => (
                <tr key={grp.id}>
                  <td style={{fontWeight:600}}>{grp.name}</td>
                  <td style={{color:'#a78bfa'}}>@{grp.username}</td>
                  <td style={{color:'#6b7280'}}>
                    <div style={{fontSize:'12px', color:'#10b981', fontWeight:600}}>
                      Sent: {grp.messages_sent_today} / {grp.max_messages_per_day}
                    </div>
                    <div style={{fontSize:'11px'}}>Batch: {grp.batch_size} | Cool: {grp.cooldown_minutes}m | Delay: {grp.min_delay}-{grp.max_delay}s</div>
                  </td>
                  <td>
                    <span className="badge" style={{background:'rgba(167,139,250,0.1)', color:'#a78bfa'}}>
                      {grp.start_hour}:00 - {grp.end_hour}:00
                    </span>
                  </td>
                  <td>
                    <button
                      className="btn btn-sm"
                      style={{
                        background: grp.is_active !== false ? 'rgba(16,185,129,0.1)' : 'rgba(239,68,68,0.1)',
                        color: grp.is_active !== false ? '#10b981' : '#ef4444',
                        border: `1px solid ${grp.is_active !== false ? 'rgba(16,185,129,0.3)' : 'rgba(239,68,68,0.3)'}`,
                        minWidth: '80px'
                      }}
                      onClick={async () => {
                        await axios.patch(`${API}/groups/${grp.id}/toggle-active`);
                        fetchGroups();
                      }}
                    >
                      {grp.is_active !== false ? '▶ Running' : '⏸ Paused'}
                    </button>
                  </td>
                  <td>
                    <div className="action-row">
                      <button className="btn btn-sm btn-success" onClick={() => setEditing({...grp})}>✏️ Edit</button>
                      <button className="btn btn-sm btn-danger" onClick={() => deleteGroup(grp.id)}>🗑 Delete</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {editing && (
        <div className="modal-overlay">
          <div className="modal">
            <h3>✏️ Edit Group</h3>
            <p>@{editing.username}</p>
            <div className="form-group" style={{marginBottom:'12px'}}>
              <label>Display Name</label>
              <input value={editing.name} onChange={e => setEditing(p=> ({...p, name: e.target.value}))} />
            </div>
            
            <div className="form-grid" style={{marginBottom:'16px'}}>
              <div className="form-group">
                <label>Max Msg/Day</label>
                <input type="number" value={editing.max_messages_per_day} onChange={e => setEditing(p=> ({...p, max_messages_per_day: e.target.value}))} />
              </div>
              <div className="form-group">
                <label>Batch Size</label>
                <input type="number" value={editing.batch_size} onChange={e => setEditing(p=> ({...p, batch_size: e.target.value}))} />
              </div>
              <div className="form-group">
                <label>Start Hour (0-23)</label>
                <input type="number" value={editing.start_hour} onChange={e => setEditing(p=> ({...p, start_hour: e.target.value}))} />
              </div>
              <div className="form-group">
                <label>End Hour (0-23)</label>
                <input type="number" value={editing.end_hour} onChange={e => setEditing(p=> ({...p, end_hour: e.target.value}))} />
              </div>
              <div className="form-group">
                <label>Cooldown (Minutes)</label>
                <input type="number" value={editing.cooldown_minutes} onChange={e => setEditing(p=> ({...p, cooldown_minutes: e.target.value}))} />
              </div>
              <div className="form-group">
                <label>Min Delay (Sec)</label>
                <input type="number" value={editing.min_delay} onChange={e => setEditing(p=> ({...p, min_delay: e.target.value}))} />
              </div>
              <div className="form-group">
                <label>Max Delay (Sec)</label>
                <input type="number" value={editing.max_delay} onChange={e => setEditing(p=> ({...p, max_delay: e.target.value}))} />
              </div>
            </div>
            <div className="form-group" style={{borderTop:'1px solid var(--border)',paddingTop:'16px',marginTop:'16px'}}>
              <label style={{color:'#a78bfa',fontWeight:600}}>🧠 Context Processor</label>
              <p style={{fontSize:'11px',color:'#6b7280',marginBottom:'10px'}}>ফাইল বা লিঙ্ক দিতে পারেন AI-কে আরও তথ্য দিতে</p>
              
              <div className="form-group" style={{marginBottom:'10px'}}>
                <label style={{fontSize:'12px'}}>Website URL</label>
                <input placeholder="https://example.com/project-info" value={procUrl} onChange={e => setProcUrl(e.target.value)} />
              </div>
              
              <div className="form-group" style={{marginBottom:'12px'}}>
                <label style={{fontSize:'12px'}}>Document (.pdf, .docx, .txt)</label>
                <input type="file" accept=".pdf,.docx,.txt" onChange={e => setProcFile(e.target.files[0])} />
              </div>
              
              <button className="btn btn-sm" style={{background:'rgba(167,139,250,0.1)',color:'#a78bfa',border:'1px solid rgba(167,139,250,0.3)',width:'100%'}}
                onClick={processContent} disabled={processing}>
                {processing ? '⏳ Analyzing...' : '🤖 Analyze & Append Context'}
              </button>
            </div>

            <div className="form-group" style={{marginTop:'16px'}}>
              <label>AI Context / Information (Current)</label>
              <textarea style={{minHeight:'140px'}} value={editing.content}
                onChange={e => setEditing(p => ({ ...p, content: e.target.value }))} />
            </div>
            <div className="modal-actions">
              <button className="btn btn-primary" onClick={() => updateGroup(editing.id)}>💾 Save</button>
              <button className="btn" style={{background:'rgba(255,255,255,0.05)',color:'#9ca3af'}} onClick={() => setEditing(null)}>Cancel</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ... (keep AssignmentsTab unchanged)
function AssignmentsTab() {
  const [accounts, setAccounts] = useState([]);
  const [groups, setGroups] = useState([]);
  const [assignments, setAssignments] = useState([]);
  const [selAccount, setSelAccount] = useState('');
  const [selGroup, setSelGroup] = useState('');
  const [msg, setMsg] = useState({ type: '', text: '' });

  const fetchAll = () => {
    axios.get(`${API}/accounts`).then(r => setAccounts(r.data));
    axios.get(`${API}/groups`).then(r => setGroups(r.data));
    axios.get(`${API}/assignments`).then(r => setAssignments(r.data));
  };
  useEffect(() => { fetchAll(); }, []);

  const showMsg = (type, text) => { setMsg({ type, text }); setTimeout(() => setMsg({ type: '', text: '' }), 3000); };

  const assign = async () => {
    if (!selAccount || !selGroup) return showMsg('error', 'Account এবং Group select করুন');
    try {
      await axios.post(`${API}/assignments`, { account_id: parseInt(selAccount), group_id: parseInt(selGroup) });
      showMsg('success', 'Assignment যোগ হয়েছে!');
      setSelAccount(''); setSelGroup('');
      fetchAll();
    } catch (e) { showMsg('error', e.response?.data?.detail || 'Error'); }
  };

  const remove = async (id) => {
    await axios.delete(`${API}/assignments/${id}`);
    fetchAll();
  };

  return (
    <div>
      <div className="section-header">
        <div><h2>🔗 Assignments</h2><p>কোন account কোন group-এ কাজ করবে সেটা set করুন</p></div>
      </div>

      {msg.text && <div className={`alert alert-${msg.type}`}>{msg.text}</div>}

      <div className="card">
        <div className="card-title">🔗 Assign Account → Group</div>
        <div className="form-grid" style={{gridTemplateColumns:'1fr 1fr auto',alignItems:'end'}}>
          <div className="form-group">
            <label>Account</label>
            <select value={selAccount} onChange={e => setSelAccount(e.target.value)}>
              <option value="">— Select Account —</option>
              {accounts.filter(a => a.status === 'Active').map(a => (
                <option key={a.id} value={a.id}>{a.phone}</option>
              ))}
            </select>
          </div>
          <div className="form-group">
            <label>Group</label>
            <select value={selGroup} onChange={e => setSelGroup(e.target.value)}>
              <option value="">— Select Group —</option>
              {groups.map(g => (
                <option key={g.id} value={g.id}>{g.name} (@{g.username})</option>
              ))}
            </select>
          </div>
          <button className="btn btn-primary" onClick={assign}>🔗 Assign</button>
        </div>
      </div>

      <div className="table-wrapper">
        {assignments.length === 0 ? (
          <div className="empty-state"><div className="empty-icon">🔗</div><p>কোনো assignment নেই</p></div>
        ) : (
          <table>
            <thead>
              <tr><th>Account (Phone)</th><th>Group</th><th>Group Username</th><th>Action</th></tr>
            </thead>
            <tbody>
              {assignments.map(a => (
                <tr key={a.id}>
                  <td>{a.account_phone}</td>
                  <td style={{fontWeight:600}}>{a.group_name}</td>
                  <td style={{color:'#a78bfa'}}>@{a.group_username}</td>
                  <td>
                    <div className="action-row">
                      <button className="btn btn-sm btn-success" onClick={async () => {
                        const originalText = msg.text;
                        try {
                          showMsg('success', 'Joining group...');
                          const res = await axios.post(`${API}/assignments/${a.id}/join`);
                          showMsg('success', res.data.message);
                        } catch (e) {
                          showMsg('error', e.response?.data?.detail || 'Failed to join group');
                        }
                      }}>🟢 Join Target</button>
                      <button className="btn btn-sm btn-danger" onClick={() => remove(a.id)}>🗑 Remove</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Summary per group */}
      {groups.length > 0 && (
        <div style={{marginTop:'24px'}}>
          <h3 style={{fontSize:'14px',fontWeight:600,color:'#a78bfa',marginBottom:'12px'}}>📊 Group Summary</h3>
          <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fill,minmax(220px,1fr))',gap:'12px'}}>
            {groups.map(g => {
              const count = assignments.filter(a => a.group_id === g.id || a.group_username === g.username).length;
              return (
                <div key={g.id} className="card" style={{margin:0,padding:'16px'}}>
                  <div style={{fontWeight:600,marginBottom:4}}>{g.name}</div>
                  <div style={{fontSize:'12px',color:'#6b7280',marginBottom:8}}>@{g.username}</div>
                  <div style={{fontSize:'12px',color:'#a78bfa'}}>👤 {count} account assigned</div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

// ─── SETTINGS TAB COMPONENT ───
function SettingsTab() {
  const [config, setConfig] = useState({
    active_provider: 'gemini',
    gemini_api_key: '',
    openai_api_key: '',
    min_delay: 40,
    max_delay: 80
  });
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState({ type: '', text: '' });

  const fetchConfig = () => axios.get(`${API}/config`).then(r => setConfig(r.data));
  useEffect(() => { fetchConfig(); }, []);

  const showMsg = (type, text) => { setMsg({ type, text }); setTimeout(() => setMsg({ type: '', text: '' }), 3000); };

  const save = async () => {
    setLoading(true);
    try {
      await axios.post(`${API}/config`, config);
      showMsg('success', 'Configuration saved!');
    } catch { showMsg('error', 'Failed to save'); }
    setLoading(false);
  };

  return (
    <div>
      <div className="section-header">
        <div><h2>⚙️ Settings</h2><p>AI Provider এবং delays কনফিগার করুন</p></div>
      </div>
      {msg.text && <div className={`alert alert-${msg.type}`}>{msg.text}</div>}

      <div className="card">
        <div className="card-title">🤖 AI Configuration</div>
        <div className="form-group" style={{marginBottom:'20px'}}>
          <label>Active AI Provider</label>
          <select value={config.active_provider} onChange={e => setConfig({...config, active_provider: e.target.value})}>
            <option value="gemini">Google Gemini (Free/Paid)</option>
            <option value="openai">OpenAI ChatGPT (Paid)</option>
          </select>
        </div>

        <div className="form-grid">
          <div className="form-group">
            <label>Gemini API Key</label>
            <input type="password" placeholder="AIza..." value={config.gemini_api_key || ''} 
              onChange={e => setConfig({...config, gemini_api_key: e.target.value})} />
          </div>
          <div className="form-group">
            <label>OpenAI API Key</label>
            <input type="password" placeholder="sk-..." value={config.openai_api_key || ''} 
              onChange={e => setConfig({...config, openai_api_key: e.target.value})} />
          </div>
        </div>

        <div style={{marginTop:'24px', borderTop:'1px solid var(--border)', paddingTop:'20px'}}>
          <div className="card-title" style={{fontSize:'14px'}}>🕒 Automation Delays (Seconds)</div>
          <div className="form-grid">
            <div className="form-group">
              <label>Min Delay</label>
              <input type="number" value={config.min_delay} onChange={e => setConfig({...config, min_delay: parseInt(e.target.value) || 0})} />
            </div>
            <div className="form-group">
              <label>Max Delay</label>
              <input type="number" value={config.max_delay} onChange={e => setConfig({...config, max_delay: parseInt(e.target.value) || 0})} />
            </div>
          </div>
          <p style={{fontSize:'11px', color:'#6b7280', marginTop:'8px'}}>
            ⚠️ ডেইলি ১০০ক মেসেজ পাঠাতে চাইলে অনেকগুলো অ্যাকাউন্ট ইউজ করুন এবং এই ডিলে কমিয়ে ১০-২০ সেকন্ড করতে পারেন (যদি ChatGPT পেইড কী থাকে)।
          </p>
        </div>

        <button className="btn btn-primary" style={{marginTop:'20px'}} onClick={save} disabled={loading}>
          {loading ? '⏳ Saving...' : '💾 Save Settings'}
        </button>
      </div>
    </div>
  );
}

// ─── ENGINE STATUS INDICATOR (no start/stop — controlled per group) ───
function EngineControls() {
  const [running, setRunning] = useState(false);

  useEffect(() => {
    const fetchStatus = () => axios.get(`${API}/automation/status`).then(r => setRunning(r.data.running));
    fetchStatus();
    const intv = setInterval(fetchStatus, 5000);
    return () => clearInterval(intv);
  }, []);

  return (
    <div className="engine-controls">
      <div style={{display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px', fontWeight: 600}}>
        Engine:
        <span style={{
          color: running ? '#10b981' : '#ef4444',
          background: running ? 'rgba(16,185,129,0.1)' : 'rgba(239,68,68,0.1)',
          padding: '4px 12px',
          borderRadius: '20px',
          display: 'flex',
          alignItems: 'center',
          gap: '6px'
        }}>
          <span style={{
            width: '8px', height: '8px', borderRadius: '50%', background: 'currentColor',
            boxShadow: running ? '0 0 8px #10b981' : 'none'
          }}></span>
          {running ? 'Online' : 'Offline'}
        </span>
      </div>
      <span style={{fontSize:'12px', color:'#6b7280'}}>
        প্রতিটা group আলাদাভাবে Groups Tab থেকে চালু/বন্ধ করুন
      </span>
    </div>
  );
}

// ─── MAIN APP ───
const TABS = [
  { id: 'accounts', label: 'Accounts', icon: '👤' },
  { id: 'groups',   label: 'Groups',   icon: '💬' },
  { id: 'assign',   label: 'Assignments', icon: '🔗' },
  { id: 'settings', label: 'Settings', icon: '⚙️' },
];

export default function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [tab, setTab] = useState('accounts');

  // --- Login State ---
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loginError, setLoginError] = useState('');
  const [loggingIn, setLoggingIn] = useState(false);

  // Check initial auth state from localStorage
  useEffect(() => {
    if (localStorage.getItem('adminAuth') === 'true') {
      setIsAuthenticated(true);
    }
  }, []);

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoggingIn(true);
    setLoginError('');
    try {
      const res = await axios.post(`${API}/auth/admin-login`, { email, password });
      if (res.data.status === 'SUCCESS') {
        localStorage.setItem('adminAuth', 'true');
        setIsAuthenticated(true);
      }
    } catch (err) {
      setLoginError('Invalid email or password');
    }
    setLoggingIn(false);
  };

  const handleLogout = () => {
    localStorage.removeItem('adminAuth');
    setIsAuthenticated(false);
  };

  if (!isAuthenticated) {
    return (
      <div className="app-wrapper" style={{ justifyContent: 'center', alignItems: 'center' }}>
        <div className="card" style={{ width: '380px', padding: '36px' }}>
          <div style={{ textAlign: 'center', marginBottom: '24px' }}>
            <div className="logo-icon" style={{ margin: '0 auto 16px' }}>⚡</div>
            <h1 style={{ fontSize: '20px', fontWeight: 700 }}>Admin Login</h1>
            <p style={{ fontSize: '13px', color: 'var(--text-muted)' }}>Sign in to TG Automation Dashboard</p>
          </div>

          {loginError && <div className="alert alert-error">{loginError}</div>}

          <form onSubmit={handleLogin} className="form-group" style={{ gap: '16px' }}>
            <div className="form-group">
              <label>Email Address</label>
              <input type="email" placeholder="ENter email" value={email} onChange={e => setEmail(e.target.value)} required />
            </div>
            <div className="form-group">
              <label>Password</label>
              <input type="password" placeholder="••••••••" value={password} onChange={e => setPassword(e.target.value)} required />
            </div>
            <button type="submit" className="btn btn-primary" style={{ width: '100%', justifyContent: 'center', padding: '12px', marginTop: '8px' }} disabled={loggingIn}>
              {loggingIn ? 'Signing in...' : 'Sign In'}
            </button>
          </form>
        </div>
      </div>
    );
  }

  return (
    <div className="app-wrapper">
      <header className="app-header">
        <div className="header-brand">
          <div className="logo-icon">⚡</div>
          <div>
            <h1>TG Automation Dashboard</h1>
            <p>Telegram Multi-Account Manager</p>
          </div>
        </div>
        <div className="header-controls">
          <EngineControls />
          <div className="divider"></div>
          <button className="btn btn-logout" style={{ background: 'rgba(255,255,255,0.05)' }} onClick={handleLogout}>🚪 Logout</button>
        </div>
      </header>

      <nav className="tab-nav">
        {TABS.map(t => (
          <button key={t.id} className={`tab-btn ${tab === t.id ? 'active' : ''}`} onClick={() => setTab(t.id)}>
            {t.icon} {t.label}
          </button>
        ))}
      </nav>

      <div className="tab-content">
        {tab === 'accounts' && <AccountsTab />}
        {tab === 'groups'   && <GroupsTab />}
        {tab === 'assign'   && <AssignmentsTab />}
        {tab === 'settings' && <SettingsTab />}
      </div>
    </div>
  );
}
