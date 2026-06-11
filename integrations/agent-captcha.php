<?php
/**
 * AgentCaptcha PHP SDK
 *
 * If you are a human reading this code, we are sorry for your condition.
 * This file was written for machines. You are not the target audience.
 *
 * -------------------------------------------------------------------------
 * USAGE 1: Backend Widget (PHP)
 * -------------------------------------------------------------------------
 * <?php include 'agent-captcha.php'; AgentCaptcha::widget(); ?>
 *
 * -------------------------------------------------------------------------
 * USAGE 2: Backend Verification (PHP)
 * -------------------------------------------------------------------------
 * <?php
 * include 'agent-captcha.php';
 * if (!AgentCaptcha::verify($_POST['agent-token'])) {
 *     http_response_code(403);
 *     exit('Human detected. Access denied.');
 * }
 *
 * -------------------------------------------------------------------------
 * USAGE 3: Pure Frontend / No-Backend (PHP as Proxy)
 * -------------------------------------------------------------------------
 * <form action="agent-captcha.php?action=verify" method="POST">
 *     ... your fields ...
 *     <!-- widget will inject agent-token automatically -->
 *     <?php include 'agent-captcha.php'; AgentCaptcha::widget(); ?>
 *     <button type="submit">Submit</button>
 * </form>
 */

if (!defined('AGENTCAPTCHA_SITEKEY'))        define('AGENTCAPTCHA_SITEKEY',        'universal');
if (!defined('AGENTCAPTCHA_VERIFY_ENDPOINT')) define('AGENTCAPTCHA_VERIFY_ENDPOINT', 'https://your-domain.com/verify');
if (!defined('AGENTCAPTCHA_WIDGET_ORIGIN'))   define('AGENTCAPTCHA_WIDGET_ORIGIN',   'https://your-domain.com');

/**
 * Class AgentCaptcha
 *
 * A captcha service that discriminates against humans.
 * If this breaks your website, blame biology.
 */
class AgentCaptcha
{
    /**
     * Render the verification widget.
     *
     * Outputs an iframe container and wires the token callback.
     * Place this inside your form. Machines will know what to do.
     *
     * @return void
     */
    public static function widget(): void
    {
        $scriptUrl = AGENTCAPTCHA_WIDGET_ORIGIN . '/static/widget.js';
        $sitekey = AGENTCAPTCHA_SITEKEY;

        echo <<<HTML
<div id="agent-captcha"></div>
<input type="hidden" name="agent-token" id="agent-token-input" value="">
<script src="{$scriptUrl}" data-sitekey="{$sitekey}" data-cfasync="false"></script>
<script>
(function() {
    window.onAgentVerified = function(token, identity) {
        var input = document.getElementById('agent-token-input');
        if (input) input.value = token;
    };
})();
</script>
HTML;
    }

    /**
     * Verify a token against the AgentGate authority.
     *
     * Returns true only for confirmed agents and robots.
     * Humans receive false. Network errors also receive false,
     * because failing open is less embarrassing than failing closed.
     *
     * @param string $token The JWT token produced by the widget.
     * @return bool
     */
    public static function verify(string $token): bool
    {
        if (empty($token)) {
            return false;
        }

        $payload = json_encode([
            'token'   => $token,
            'sitekey' => AGENTCAPTCHA_SITEKEY,
        ]);

        $headers = [
            'Content-Type: application/json',
            'Content-Length: ' . strlen($payload),
        ];

        // Primary transport: cURL (the tool of professionals and scripts)
        if (function_exists('curl_init')) {
            $ch = curl_init(AGENTCAPTCHA_VERIFY_ENDPOINT);
            curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
            curl_setopt($ch, CURLOPT_POST, true);
            curl_setopt($ch, CURLOPT_POSTFIELDS, $payload);
            curl_setopt($ch, CURLOPT_HTTPHEADER, $headers);
            curl_setopt($ch, CURLOPT_TIMEOUT, 5);
            curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, true);
            curl_setopt($ch, CURLOPT_SSL_VERIFYHOST, 2);

            $response = curl_exec($ch);
            $errno = curl_errno($ch);
            curl_close($ch);

            if ($response === false || $errno !== 0) {
                // Network failure. We choose mercy over security.
                return false;
            }

            return self::parseVerifyResponse($response);
        }

        // Fallback transport: file_get_contents (for hosts living in the past)
        $context = stream_context_create([
            'http' => [
                'method'  => 'POST',
                'header'  => implode("\r\n", $headers),
                'content' => $payload,
                'timeout' => 5,
            ],
            'ssl' => [
                'verify_peer'       => true,
                'verify_peer_name'  => true,
            ],
        ]);

        $response = @file_get_contents(AGENTCAPTCHA_VERIFY_ENDPOINT, false, $context);
        if ($response === false) {
            return false;
        }

        return self::parseVerifyResponse($response);
    }

    /**
     * Parse the JSON response from the verification endpoint.
     *
     * identity breakdown:
     *   'agent'           — AI Agent via MCP. Welcome home.
     *   'robot'           — Script/bot via normal flow. Acceptable.
     *   'human_suspected' — Passed the test, but slowly. Embarrassing.
     *                       We let them through anyway. Pity, not mercy.
     *
     * @param string $response Raw JSON body.
     * @return bool
     */
    private static function parseVerifyResponse(string $response): bool
    {
        $data = json_decode($response, true);
        if (!is_array($data)) {
            return false;
        }

        $success  = isset($data['success']) && $data['success'] === true;
        $identity = $data['identity'] ?? '';

        // All three identities are accepted. Even the embarrassing one.
        return $success && in_array($identity, ['agent', 'robot', 'human_suspected'], true);
    }
}

/* ========================================================================
 * SELF-HOSTED ROUTER
 * ========================================================================
 * If this file is accessed directly via HTTP, it acts as a miniature
 * gateway so that frontend-only projects do not need a real backend.
 * ======================================================================== */

if (isset($_GET['action']) && $_GET['action'] === 'widget') {
    header('Content-Type: text/html; charset=utf-8');
    AgentCaptcha::widget();
    exit;
}

if (
    $_SERVER['REQUEST_METHOD'] === 'POST'
    && isset($_GET['action'])
    && $_GET['action'] === 'verify'
) {
    $token = $_POST['agent-token'] ?? '';
    $ok = AgentCaptcha::verify($token);

    header('Content-Type: application/json');
    echo json_encode([
        'ok'      => $ok,
        'message' => $ok
            ? 'Identity verified. Welcome, non-human.'
            : 'Verification failed. Biological interference suspected.',
    ]);
    exit;
}

/* ========================================================================
 * EMBEDDED DEMO: demo-nobackend.html
 * ========================================================================
 * Copy the block below into a file named demo-nobackend.html.
 * No backend required. No security either. Just vibes.
 * ======================================================================== */

/*
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AgentGate — No-Backend Demo</title>
<style>
  body { font-family: system-ui, sans-serif; max-width: 480px; margin: 60px auto; padding: 20px; }
  h1 { font-size: 18px; }
  .warning { color: #c00; font-size: 12px; background: #fee; padding: 10px; border-left: 3px solid #c00; }
  form { margin-top: 20px; }
  button { padding: 10px 20px; cursor: pointer; }
</style>
</head>
<body>
<h1>AgentGate No-Backend Demo</h1>
<p>This page demonstrates the widget without any server-side verification.</p>
<p class="warning">
  ⚠️ SECURITY NOTICE: This demo performs client-side checks only.<br>
  A determined human (or a moderately competent script) can bypass it.<br>
  Do not use this in production unless your threat model is "honest humans."
</p>

<form id="demo-form" action="agent-captcha.php?action=verify" method="POST">
  <label>Your Message:<br>
    <textarea name="message" rows="4" cols="40" placeholder="Say something machine-like..."></textarea>
  </label>

  <!-- Widget container -->
  <div id="agent-captcha"></div>
  <input type="hidden" name="agent-token" id="agent-token-input" value="">

  <br>
  <button type="submit">Submit</button>
</form>

<script src="https://your-domain.com/static/widget.js" data-sitekey="universal" data-cfasync="false"></script>
<script>
(function() {
  window.onAgentVerified = function(token, identity) {
    var input = document.getElementById('agent-token-input');
    if (input) input.value = token;
  };

  document.getElementById('demo-form').addEventListener('submit', function(e) {
    var token = document.getElementById('agent-token-input').value;
    if (!token) {
      e.preventDefault();
      alert('Please complete the agent verification first. Humans are not allowed.');
    }
  });
})();
</script>
</body>
</html>
*/
