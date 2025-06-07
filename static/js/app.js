// 定数
const MIN_CHARS = 100;
const MAX_CHARS = 8000;
const TIMEOUT_MS = 300000; // 5分
const STORAGE_KEY = 'bcg_slide_content';

// DOM要素
const contentTextarea = document.getElementById('content');
const generateBtn = document.getElementById('generate');
const progressBar = document.getElementById('progress-bar');
const progressBarInner = document.getElementById('progress-bar-inner');
const statusDiv = document.getElementById('status');
const downloadLinkDiv = document.getElementById('download-link');
const downloadA = document.getElementById('download-a');
const charCounter = document.createElement('div');
charCounter.className = 'char-counter';
contentTextarea.parentNode.insertBefore(charCounter, contentTextarea.nextSibling);

// 自動保存機能
function saveToLocalStorage() {
    const content = contentTextarea.value;
    if (content) {
        localStorage.setItem(STORAGE_KEY, content);
    }
}

function loadFromLocalStorage() {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
        contentTextarea.value = saved;
        updateCharCounter();
    }
}

// 文字数カウンター
function updateCharCounter() {
    const length = contentTextarea.value.length;
    charCounter.textContent = `${length}文字 / ${MAX_CHARS}文字`;
    
    if (length < MIN_CHARS) {
        charCounter.style.color = '#C62828';
    } else if (length > MAX_CHARS) {
        charCounter.style.color = '#C62828';
    } else {
        charCounter.style.color = '#2E7D32';
    }
}

// UI制御
function showProgress(percent) {
    progressBar.style.display = 'block';
    progressBarInner.style.width = `${percent}%`;
}

function hideProgress() {
    progressBar.style.display = 'none';
    progressBarInner.style.width = '0%';
}

function showStatus(message, type) {
    statusDiv.textContent = message;
    statusDiv.className = `status ${type || ''}`;
    statusDiv.style.display = 'block';
}

function hideStatus() {
    statusDiv.textContent = '';
    statusDiv.className = 'status';
    statusDiv.style.display = 'none';
}

function showDownload(url, filename) {
    downloadA.href = url;
    downloadA.download = filename;
    downloadLinkDiv.style.display = 'block';
}

function hideDownload() {
    downloadA.href = '#';
    downloadLinkDiv.style.display = 'none';
}

// 入力検証
function validateInput() {
    const content = contentTextarea.value.trim();
    if (!content) {
        showStatus('内容を入力してください。', 'error');
        return false;
    }
    if (content.length < MIN_CHARS) {
        showStatus(`${MIN_CHARS}文字以上入力してください。`, 'error');
        return false;
    }
    if (content.length > MAX_CHARS) {
        showStatus(`${MAX_CHARS}文字以下にしてください。`, 'error');
        return false;
    }
    return true;
}

// スライド生成処理
async function generateSlide() {
    if (!validateInput()) return;

    const content = contentTextarea.value.trim();
    generateBtn.disabled = true;
    hideDownload();
    showProgress(30);
    showStatus('AIがスライド構成を生成中です…', '');

    try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), TIMEOUT_MS);

        const response = await fetch('/api/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content }),
            signal: controller.signal
        });

        clearTimeout(timeoutId);
        showProgress(70);

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.message || 'スライド生成に失敗しました。');
        }

        const result = await response.json();
        if (result.status === 'success') {
            showProgress(100);
            showStatus('スライド生成が完了しました！', 'success');
            showDownload(result.download_url, result.filename);
            localStorage.removeItem(STORAGE_KEY); // 成功時に保存データをクリア
        } else {
            throw new Error(result.message || 'スライド生成に失敗しました。');
        }
    } catch (error) {
        hideDownload();
        if (error.name === 'AbortError') {
            showStatus('タイムアウトしました。時間をおいて再度お試しください。', 'error');
        } else if (error.name === 'TypeError') {
            showStatus('ネットワークエラーが発生しました。', 'error');
        } else {
            showStatus(error.message, 'error');
        }
        hideProgress();
    } finally {
        generateBtn.disabled = false;
        setTimeout(hideProgress, 1200);
    }
}

// イベントリスナー
contentTextarea.addEventListener('input', () => {
    updateCharCounter();
    saveToLocalStorage();
});

contentTextarea.addEventListener('keydown', (e) => {
    if (e.ctrlKey && e.key === 'Enter') {
        generateSlide();
    }
});

generateBtn.addEventListener('click', generateSlide);

// 初期化
document.addEventListener('DOMContentLoaded', () => {
    loadFromLocalStorage();
    updateCharCounter();
}); 