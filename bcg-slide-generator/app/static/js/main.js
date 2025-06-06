document.addEventListener('DOMContentLoaded', function() {
    // フォーム要素の取得
    const uploadForm = document.getElementById('uploadForm');
    const generateForm = document.getElementById('generateForm');
    const resultDiv = document.getElementById('result');

    // デザインファイルのアップロード処理
    if (uploadForm) {
        uploadForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const fileInput = document.getElementById('designFile');
            const categorySelect = document.getElementById('category');
            const qualitySelect = document.getElementById('quality');
            
            if (!fileInput || !categorySelect || !qualitySelect) {
                showError('フォームの要素が見つかりません。');
                return;
            }
            
            const file = fileInput.files[0];
            
            if (!file) {
                showError('ファイルを選択してください。');
                return;
            }

            const formData = new FormData();
            formData.append('files', file);
            formData.append('category', categorySelect.value);
            formData.append('quality', qualitySelect.value);

            try {
                showLoading('デザインファイルをアップロード中...');
                
                const response = await fetch('/api/upload-design', {
                    method: 'POST',
                    body: formData
                });

                const data = await response.json();

                if (response.ok) {
                    showSuccess('デザインファイルが正常にアップロードされました。');
                } else {
                    showError(data.error || 'アップロードに失敗しました。');
                }
            } catch (error) {
                showError('エラーが発生しました。');
                console.error('Upload error:', error);
            }
        });
    }

    // スライド生成処理
    generateForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const content = document.getElementById('content').value;
        
        if (!content.trim()) {
            showError('プレゼンテーション内容を入力してください。');
            return;
        }

        try {
            showLoading('スライドを生成中...');
            
            const response = await fetch('/api/generate-slides', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ content: content })
            });

            const data = await response.json();

            if (response.ok) {
                showSuccess('スライドが正常に生成されました。');
                // 生成されたスライドのダウンロードリンクを表示
                const downloadLink = document.createElement('a');
                downloadLink.href = data.download_url;
                downloadLink.className = 'btn btn-primary mt-3';
                downloadLink.textContent = 'スライドをダウンロード';
                resultDiv.appendChild(downloadLink);
            } else {
                showError(data.error || 'スライドの生成に失敗しました。');
            }
        } catch (error) {
            showError('エラーが発生しました。');
            console.error('Generation error:', error);
        }
    });

    // ローディング表示
    function showLoading(message) {
        resultDiv.innerHTML = `
            <div class="text-center">
                <div class="loading mb-3"></div>
                <p>${message}</p>
            </div>
        `;
    }

    // エラーメッセージ表示
    function showError(message) {
        resultDiv.innerHTML = `
            <div class="error-message">
                <i class="fas fa-exclamation-circle"></i>
                ${message}
            </div>
        `;
    }

    // 成功メッセージ表示
    function showSuccess(message) {
        resultDiv.innerHTML = `
            <div class="success-message">
                <i class="fas fa-check-circle"></i>
                ${message}
            </div>
        `;
    }
}); 