/**
 * Node.js / Express 后端验证示例
 */

const express = require('express');
const axios = require('axios');

const AGENT_CAPTCHA_VERIFY_URL = 'https://your-domain.com/verify';
const YOUR_SITEKEY = 'demo_sitekey';

const app = express();
app.use(express.json());

app.post('/submit', async (req, res) => {
    const token = req.body.token || req.body['agent-token'];
    if (!token) {
        return res.status(400).json({ error: 'Missing token' });
    }

    try {
        const { data } = await axios.post(AGENT_CAPTCHA_VERIFY_URL, {
            token,
            sitekey: YOUR_SITEKEY,
        });

        if (data.success && ['agent', 'robot'].includes(data.identity)) {
            return res.json({ ok: true, identity: data.identity });
        }
        return res.status(403).json({ ok: false, reason: data.message });
    } catch (e) {
        return res.status(500).json({ error: 'Verification failed' });
    }
});

app.listen(3000, () => console.log('Demo server on :3000'));
