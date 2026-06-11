(function() {
    'use strict';

    // --- Mouse tracking ---
    let lastX = 0, lastY = 0;
    let moveCount = 0;
    let totalDelta = 0;

    document.addEventListener('mousemove', function(e) {
        if (moveCount > 0) {
            const dx = e.clientX - lastX;
            const dy = e.clientY - lastY;
            totalDelta += Math.sqrt(dx*dx + dy*dy);
        }
        lastX = e.clientX;
        lastY = e.clientY;
        moveCount++;
    });

    // --- Focus tracking ---
    let focusSwitches = 0;
    document.addEventListener('visibilitychange', function() {
        if (document.hidden) {
            focusSwitches++;
        }
    });

    // --- Keyboard entropy tracking ---
    let keyTimestamps = [];
    document.addEventListener('keydown', function(e) {
        // Ignore modifier-only keys
        if (['Shift', 'Control', 'Alt', 'Meta', 'CapsLock', 'Tab'].indexOf(e.key) !== -1) return;
        keyTimestamps.push(performance.now());
        // Keep last 50 timestamps
        if (keyTimestamps.length > 50) keyTimestamps.shift();
    });

    // --- Scroll entropy tracking ---
    let lastScrollY = window.scrollY;
    let scrollEvents = [];
    let lastScrollTime = performance.now();
    window.addEventListener('scroll', function() {
        const now = performance.now();
        const delta = window.scrollY - lastScrollY;
        const dt = now - lastScrollTime;
        if (dt > 0) {
            scrollEvents.push({ delta: delta, speed: Math.abs(delta) / dt });
            if (scrollEvents.length > 30) scrollEvents.shift();
        }
        lastScrollY = window.scrollY;
        lastScrollTime = now;
    }, { passive: true });

    // --- Click precision tracking ---
    let clickOffsets = [];
    document.addEventListener('click', function(e) {
        const target = e.target;
        if (!target || !target.getBoundingClientRect) return;
        const rect = target.getBoundingClientRect();
        const centerX = rect.left + rect.width / 2;
        const centerY = rect.top + rect.height / 2;
        const offset = Math.sqrt((e.clientX - centerX)**2 + (e.clientY - centerY)**2);
        clickOffsets.push(offset);
        if (clickOffsets.length > 20) clickOffsets.shift();
    });

    // --- Computed properties ---

    // 鼠标路径熵：移动点数的对数近似
    Object.defineProperty(window, '__mouseEntropy', {
        get: function() {
            if (moveCount < 2) return 0;
            return Math.log(moveCount + 1);
        }
    });

    Object.defineProperty(window, '__focusSwitches', {
        get: function() {
            return focusSwitches;
        }
    });

    // 键盘输入熵：按键间隔的标准差，越高越不规律（人类特征）
    Object.defineProperty(window, '__keyEntropy', {
        get: function() {
            if (keyTimestamps.length < 3) return 0;
            const intervals = [];
            for (let i = 1; i < keyTimestamps.length; i++) {
                intervals.push(keyTimestamps[i] - keyTimestamps[i-1]);
            }
            const mean = intervals.reduce((a, b) => a + b, 0) / intervals.length;
            const variance = intervals.reduce((sum, v) => sum + (v - mean)**2, 0) / intervals.length;
            return Math.sqrt(variance) / 100; // 归一化到合理范围
        }
    });

    // 滚动熵：滚动速度变化的标准差
    Object.defineProperty(window, '__scrollEntropy', {
        get: function() {
            if (scrollEvents.length < 3) return 0;
            const speeds = scrollEvents.map(e => e.speed);
            const mean = speeds.reduce((a, b) => a + b, 0) / speeds.length;
            const variance = speeds.reduce((sum, v) => sum + (v - mean)**2, 0) / speeds.length;
            return Math.sqrt(variance) * 100; // 放大到合理范围
        }
    });

    // 点击精度：平均偏离元素中心的距离，越低越精准（机器特征）
    Object.defineProperty(window, '__clickPrecision', {
        get: function() {
            if (clickOffsets.length === 0) return 0;
            return clickOffsets.reduce((a, b) => a + b, 0) / clickOffsets.length;
        }
    });
})();
