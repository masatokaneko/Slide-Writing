# 運用・保守マニュアル

## 8. 日常運用手順

### 8.1 システム起動・停止手順

#### 日常起動手順
```bash
#!/bin/bash
# startup.sh - システム起動スクリプト

echo "BCG Slide Generator 起動開始..."

# 1. 環境変数の確認
if [ ! -f "config/.env" ]; then
    echo "Error: 設定ファイルが見つかりません"
    exit 1
fi

# 2. Python仮想環境の有効化
source venv/bin/activate

# 3. 依存関係のチェック
pip check

# 4. データベースの整合性チェック
python -c "
from app.database.db_manager import DatabaseManager
db = DatabaseManager('data/database.db')
print('Database connection: OK')
"

# 5. ディスク容量チェック
AVAILABLE=$(df -h data/ | awk 'NR==2 {print $4}' | sed 's/G//')
if (( $(echo "$AVAILABLE < 1" | bc -l) )); then
    echo "Warning: ディスク容量が不足しています ($AVAILABLE GB)"
fi

# 6. ログファイルのローテーション
if [ -f "logs/app.log" ] && [ $(stat -c%s "logs/app.log") -gt 104857600 ]; then
    mv logs/app.log logs/app.log.$(date +%Y%m%d_%H%M%S)
fi

# 7. キャッシュクリーンアップ
python -c "
from app.core.cache_manager import cache_manager
cleared = cache_manager.clear_expired()
print(f'Cleared {cleared} expired cache entries')
"

# 8. システム起動
echo "システムを起動しています..."
python app/main.py &

# 9. プロセスIDの保存
echo $! > app.pid

echo "システム起動完了 (PID: $!)"
echo "http://localhost:5000 でアクセス可能です"
```

#### 安全停止手順
```bash
#!/bin/bash
# shutdown.sh - システム停止スクリプト

echo "BCG Slide Generator 停止開始..."

# 1. プロセスIDの取得
if [ -f "app.pid" ]; then
    PID=$(cat app.pid)
    
    # 2. プロセスの存在確認
    if ps -p $PID > /dev/null; then
        echo "プロセス $PID を停止しています..."
        
        # 3. 通常の停止シグナル
        kill -TERM $PID
        
        # 4. 停止の確認（最大30秒待機）
        for i in {1..30}; do
            if ! ps -p $PID > /dev/null; then
                echo "プロセス停止完了"
                break
            fi
            sleep 1
        done
        
        # 5. 強制停止（必要な場合）
        if ps -p $PID > /dev/null; then
            echo "強制停止を実行します..."
            kill -KILL $PID
        fi
    else
        echo "プロセスは既に停止しています"
    fi
    
    rm app.pid
else
    echo "PIDファイルが見つかりません"
fi

# 6. バックグラウンドタスクの停止
python -c "
from app.core.background_tasks import task_manager
task_manager.shutdown()
print('Background tasks stopped')
"

echo "システム停止完了"
```

### 8.2 日常監視手順

#### システムヘルスチェック
**scripts/health_check.py**:
```python
#!/usr/bin/env python3
import requests
import json
import os
import sqlite3
import psutil
from datetime import datetime, timedelta
import logging

class SystemHealthChecker:
    def __init__(self):
        self.base_url = "http://localhost:5000"
        self.health_data = {
            'timestamp': datetime.now().isoformat(),
            'status': 'unknown',
            'checks': {}
        }
    
    def check_api_health(self):
        """API健康性チェック"""
        try:
            response = requests.get(f"{self.base_url}/api/health", timeout=5)
            if response.status_code == 200:
                self.health_data['checks']['api'] = {
                    'status': 'healthy',
                    'response_time': response.elapsed.total_seconds(),
                    'details': response.json()
                }
            else:
                self.health_data['checks']['api'] = {
                    'status': 'unhealthy',
                    'error': f"HTTP {response.status_code}"
                }
        except Exception as e:
            self.health_data['checks']['api'] = {
                'status': 'unhealthy',
                'error': str(e)
            }
    
    def check_database_health(self):
        """データベース健康性チェック"""
        try:
            conn = sqlite3.connect('data/database.db')
            cursor = conn.cursor()
            
            # 基本的なクエリテスト
            cursor.execute("SELECT COUNT(*) FROM design_assets")
            asset_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM generated_presentations")
            presentation_count = cursor.fetchone()[0]
            
            # データベースサイズ
            db_size = os.path.getsize('data/database.db')
            
            conn.close()
            
            self.health_data['checks']['database'] = {
                'status': 'healthy',
                'asset_count': asset_count,
                'presentation_count': presentation_count,
                'size_mb': round(db_size / 1024 / 1024, 2)
            }
        except Exception as e:
            self.health_data['checks']['database'] = {
                'status': 'unhealthy',
                'error': str(e)
            }
    
    def check_disk_space(self):
        """ディスク容量チェック"""
        try:
            disk_usage = psutil.disk_usage('.')
            
            free_gb = disk_usage.free / (1024**3)
            total_gb = disk_usage.total / (1024**3)
            used_percent = (disk_usage.used / disk_usage.total) * 100
            
            status = 'healthy'
            if used_percent > 90:
                status = 'critical'
            elif used_percent > 80:
                status = 'warning'
            
            self.health_data['checks']['disk_space'] = {
                'status': status,
                'free_gb': round(free_gb, 2),
                'total_gb': round(total_gb, 2),
                'used_percent': round(used_percent, 2)
            }
        except Exception as e:
            self.health_data['checks']['disk_space'] = {
                'status': 'unhealthy',
                'error': str(e)
            }
    
    def check_memory_usage(self):
        """メモリ使用量チェック"""
        try:
            memory = psutil.virtual_memory()
            
            status = 'healthy'
            if memory.percent > 90:
                status = 'critical'
            elif memory.percent > 80:
                status = 'warning'
            
            self.health_data['checks']['memory'] = {
                'status': status,
                'used_percent': memory.percent,
                'available_gb': round(memory.available / (1024**3), 2),
                'total_gb': round(memory.total / (1024**3), 2)
            }
        except Exception as e:
            self.health_data['checks']['memory'] = {
                'status': 'unhealthy',
                'error': str(e)
            }
    
    def check_log_files(self):
        """ログファイルチェック"""
        try:
            log_files = ['logs/app.log', 'logs/app_error.log']
            log_status = {}
            
            for log_file in log_files:
                if os.path.exists(log_file):
                    size_mb = os.path.getsize(log_file) / (1024**2)
                    
                    # 最近のエラーをチェック
                    recent_errors = 0
                    with open(log_file, 'r', encoding='utf-8') as f:
                        lines = f.readlines()[-100:]  # 最後の100行
                        for line in lines:
                            if 'ERROR' in line:
                                recent_errors += 1
                    
                    status = 'healthy'
                    if recent_errors > 10:
                        status = 'warning'
                    if size_mb > 100:
                        status = 'warning'
                    
                    log_status[log_file] = {
                        'status': status,
                        'size_mb': round(size_mb, 2),
                        'recent_errors': recent_errors
                    }
                else:
                    log_status[log_file] = {
                        'status': 'missing',
                        'error': 'File not found'
                    }
            
            self.health_data['checks']['logs'] = log_status
        except Exception as e:
            self.health_data['checks']['logs'] = {
                'status': 'unhealthy',
                'error': str(e)
            }
    
    def check_api_cost_usage(self):
        """API使用量・コストチェック"""
        try:
            # ログファイルからAPI使用量を集計
            today = datetime.now().date()
            monthly_cost = 0
            daily_cost = 0
            
            if os.path.exists('logs/app.log'):
                with open('logs/app.log', 'r', encoding='utf-8') as f:
                    for line in f:
                        if 'OpenAI API usage' in line:
                            try:
                                log_data = json.loads(line.split('OpenAI API usage')[1].strip())
                                log_date = datetime.fromisoformat(log_data['timestamp']).date()
                                
                                if log_date == today:
                                    daily_cost += log_data.get('cost_jpy', 0)
                                
                                if log_date.month == today.month and log_date.year == today.year:
                                    monthly_cost += log_data.get('cost_jpy', 0)
                                    
                            except:
                                continue
            
            status = 'healthy'
            if monthly_cost > 3000:  # 月間上限
                status = 'warning'
            if monthly_cost > 5000:
                status = 'critical'
            
            self.health_data['checks']['api_costs'] = {
                'status': status,
                'daily_cost_jpy': round(daily_cost, 2),
                'monthly_cost_jpy': round(monthly_cost, 2),
                'monthly_limit_jpy': 3000
            }
        except Exception as e:
            self.health_data['checks']['api_costs'] = {
                'status': 'unhealthy',
                'error': str(e)
            }
    
    def run_all_checks(self):
        """全てのヘルスチェックを実行"""
        print("システムヘルスチェック開始...")
        
        self.check_api_health()
        self.check_database_health()
        self.check_disk_space()
        self.check_memory_usage()
        self.check_log_files()
        self.check_api_cost_usage()
        
        # 全体的なステータス判定
        all_statuses = []
        for check_name, check_data in self.health_data['checks'].items():
            if isinstance(check_data, dict) and 'status' in check_data:
                all_statuses.append(check_data['status'])
            else:
                # ログファイルチェックなど、ネストした構造の場合
                for sub_check in check_data.values():
                    if isinstance(sub_check, dict) and 'status' in sub_check:
                        all_statuses.append(sub_check['status'])
        
        if 'critical' in all_statuses:
            self.health_data['status'] = 'critical'
        elif 'unhealthy' in all_statuses:
            self.health_data['status'] = 'unhealthy'
        elif 'warning' in all_statuses:
            self.health_data['status'] = 'warning'
        else:
            self.health_data['status'] = 'healthy'
        
        return self.health_data
    
    def save_health_report(self, filename=None):
        """ヘルスレポートをファイルに保存"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"health_report_{timestamp}.json"
        
        os.makedirs('reports', exist_ok=True)
        filepath = os.path.join('reports', filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.health_data, f, indent=2, ensure_ascii=False)
        
        return filepath

if __name__ == "__main__":
    checker = SystemHealthChecker()
    health_data = checker.run_all_checks()
    
    # 結果表示
    print(f"\n=== システムヘルスチェック結果 ===")
    print(f"全体ステータス: {health_data['status'].upper()}")
    print(f"チェック時刻: {health_data['timestamp']}")
    
    for check_name, check_data in health_data['checks'].items():
        print(f"\n[{check_name.upper()}]")
        if isinstance(check_data, dict) and 'status' in check_data:
            print(f"  ステータス: {check_data['status']}")
            if 'error' in check_data:
                print(f"  エラー: {check_data['error']}")
            else:
                for key, value in check_data.items():
                    if key != 'status':
                        print(f"  {key}: {value}")
        else:
            for sub_name, sub_data in check_data.items():
                print(f"  {sub_name}: {sub_data['status']}")
                if 'error' in sub_data:
                    print(f"    エラー: {sub_data['error']}")
    
    # レポート保存
    report_path = checker.save_health_report()
    print(f"\nヘルスレポートを保存しました: {report_path}")
    
    # 異常がある場合は終了コードで通知
    if health_data['status'] in ['critical', 'unhealthy']:
        exit(1)
    elif health_data['status'] == 'warning':
        exit(2)
    else:
        exit(0)
```

### 8.3 バックアップ・復旧手順

#### 自動バックアップスクリプト
**scripts/backup.py**:
```python
#!/usr/bin/env python3
import os
import shutil
import sqlite3
import json
import zipfile
from datetime import datetime, timedelta
import logging

class BackupManager:
    def __init__(self, backup_dir='backups'):
        self.backup_dir = backup_dir
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.logger = logging.getLogger(__name__)
        
        os.makedirs(backup_dir, exist_ok=True)
    
    def backup_database(self):
        """データベースのバックアップ"""
        try:
            source_db = 'data/database.db'
            backup_db = os.path.join(self.backup_dir, f'database_{self.timestamp}.db')
            
            # SQLiteのバックアップ（VACUUM込み）
            source_conn = sqlite3.connect(source_db)
            backup_conn = sqlite3.connect(backup_db)
            
            source_conn.backup(backup_conn)
            
            source_conn.close()
            backup_conn.close()
            
            # 圧縮
            compressed_backup = f"{backup_db}.zip"
            with zipfile.ZipFile(compressed_backup, 'w', zipfile.ZIP_DEFLATED) as zf:
                zf.write(backup_db, os.path.basename(backup_db))
            
            os.remove(backup_db)  # 元のファイルを削除
            
            self.logger.info(f"Database backup created: {compressed_backup}")
            return compressed_backup
            
        except Exception as e:
            self.logger.error(f"Database backup failed: {e}")
            return None
    
    def backup_design_assets(self):
        """デザインアセットのバックアップ"""
        try:
            source_dir = 'data/design_assets'
            backup_file = os.path.join(self.backup_dir, f'design_assets_{self.timestamp}.zip')
            
            if not os.path.exists(source_dir):
                self.logger.warning("Design assets directory not found")
                return None
            
            with zipfile.ZipFile(backup_file, 'w', zipfile.ZIP_DEFLATED) as zf:
                for root, dirs, files in os.walk(source_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arc_path = os.path.relpath(file_path, source_dir)
                        zf.write(file_path, arc_path)
            
            self.logger.info(f"Design assets backup created: {backup_file}")
            return backup_file
            
        except Exception as e:
            self.logger.error(f"Design assets backup failed: {e}")
            return None
    
    def backup_config(self):
        """設定ファイルのバックアップ"""
        try:
            config_dir = 'config'
            backup_file = os.path.join(self.backup_dir, f'config_{self.timestamp}.zip')
            
            with zipfile.ZipFile(backup_file, 'w', zipfile.ZIP_DEFLATED) as zf:
                for root, dirs, files in os.walk(config_dir):
                    for file in files:
                        if not file.startswith('.'):  # 秘密ファイルは除外
                            file_path = os.path.join(root, file)
                            arc_path = os.path.relpath(file_path, config_dir)
                            zf.write(file_path, arc_path)
            
            self.logger.info(f"Config backup created: {backup_file}")
            return backup_file
            
        except Exception as e:
            self.logger.error(f"Config backup failed: {e}")
            return None
    
    def backup_learned_patterns(self):
        """学習済みパターンのバックアップ"""
        try:
            # データベースから学習済みパターンを抽出
            conn = sqlite3.connect('data/database.db')
            cursor = conn.cursor()
            
            # デザインパターンの取得
            cursor.execute("""
                SELECT dp.*, da.filename, da.category 
                FROM design_patterns dp
                JOIN design_assets da ON dp.asset_id = da.id
                WHERE dp.quality_score > 0.5
            """)
            
            patterns = []
            for row in cursor.fetchall():
                patterns.append({
                    'id': row[0],
                    'asset_id': row[1],
                    'pattern_type': row[2],
                    'pattern_name': row[3],
                    'pattern_data': row[4],
                    'quality_score': row[5],
                    'filename': row[8],
                    'category': row[9]
                })
            
            conn.close()
            
            # JSONファイルとして保存
            backup_file = os.path.join(self.backup_dir, f'learned_patterns_{self.timestamp}.json')
            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump(patterns, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Learned patterns backup created: {backup_file}")
            return backup_file
            
        except Exception as e:
            self.logger.error(f"Learned patterns backup failed: {e}")
            return None
    
    def create_full_backup(self):
        """完全バックアップの作成"""
        backup_info = {
            'timestamp': self.timestamp,
            'type': 'full_backup',
            'files': [],
            'status': 'success'
        }
        
        # 各コンポーネントのバックアップ
        components = [
            ('database', self.backup_database),
            ('design_assets', self.backup_design_assets),
            ('config', self.backup_config),
            ('learned_patterns', self.backup_learned_patterns)
        ]
        
        for component_name, backup_func in components:
            backup_file = backup_func()
            if backup_file:
                backup_info['files'].append({
                    'component': component_name,
                    'file': backup_file,
                    'size_mb': round(os.path.getsize(backup_file) / (1024**2), 2)
                })
            else:
                backup_info['status'] = 'partial_failure'
        
        # バックアップ情報をJSONで保存
        info_file = os.path.join(self.backup_dir, f'backup_info_{self.timestamp}.json')
        with open(info_file, 'w', encoding='utf-8') as f:
            json.dump(backup_info, f, indent=2, ensure_ascii=False)
        
        return backup_info
    
    def cleanup_old_backups(self, days_to_keep=7):
        """古いバックアップの削除"""
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        deleted_files = []
        
        for filename in os.listdir(self.backup_dir):
            file_path = os.path.join(self.backup_dir, filename)
            file_time = datetime.fromtimestamp(os.path.getctime(file_path))
            
            if file_time < cutoff_date:
                os.remove(file_path)
                deleted_files.append(filename)
        
        self.logger.info(f"Deleted {len(deleted_files)} old backup files")
        return deleted_files

class RestoreManager:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def list_available_backups(self, backup_dir='backups'):
        """利用可能なバックアップの一覧"""
        backups = []
        
        if not os.path.exists(backup_dir):
            return backups
        
        for filename in os.listdir(backup_dir):
            if filename.startswith('backup_info_') and filename.endswith('.json'):
                info_path = os.path.join(backup_dir, filename)
                try:
                    with open(info_path, 'r', encoding='utf-8') as f:
                        backup_info = json.load(f)
                    backups.append(backup_info)
                except Exception as e:
                    self.logger.error(f"Failed to read backup info: {filename} - {e}")
        
        return sorted(backups, key=lambda x: x['timestamp'], reverse=True)
    
    def restore_database(self, backup_file):
        """データベースの復元"""
        try:
            # 現在のデータベースをバックアップ
            current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
            current_backup = f'data/database_before_restore_{current_time}.db'
            shutil.copy2('data/database.db', current_backup)
            
            # バックアップから復元
            if backup_file.endswith('.zip'):
                with zipfile.ZipFile(backup_file, 'r') as zf:
                    zf.extractall('data/temp_restore')
                    
                    # 解凍されたファイルを探す
                    for filename in os.listdir('data/temp_restore'):
                        if filename.endswith('.db'):
                            shutil.copy2(
                                os.path.join('data/temp_restore', filename),
                                'data/database.db'
                            )
                            break
                    
                    shutil.rmtree('data/temp_restore')
            else:
                shutil.copy2(backup_file, 'data/database.db')
            
            self.logger.info(f"Database restored from: {backup_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Database restore failed: {e}")
            return False
    
    def restore_design_assets(self, backup_file):
        """デザインアセットの復元"""
        try:
            # 現在のアセットをバックアップ
            if os.path.exists('data/design_assets'):
                current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_current = f'data/design_assets_before_restore_{current_time}'
                shutil.move('data/design_assets', backup_current)
            
            # バックアップから復元
            os.makedirs('data/design_assets', exist_ok=True)
            
            with zipfile.ZipFile(backup_file, 'r') as zf:
                zf.extractall('data/design_assets')
            
            self.logger.info(f"Design assets restored from: {backup_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Design assets restore failed: {e}")
            return False

# バックアップの実行例
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'restore':
        # 復元モード
        restore_manager = RestoreManager()
        backups = restore_manager.list_available_backups()
        
        if not backups:
            print("利用可能なバックアップがありません")
            exit(1)
        
        print("利用可能なバックアップ:")
        for i, backup in enumerate(backups):
            print(f"{i+1}. {backup['timestamp']} ({backup['status']})")
        
        choice = input("復元するバックアップを選択してください (番号): ")
        try:
            selected_backup = backups[int(choice) - 1]
            print(f"バックアップ {selected_backup['timestamp']} から復元しています...")
            
            for file_info in selected_backup['files']:
                if file_info['component'] == 'database':
                    restore_manager.restore_database(file_info['file'])
                elif file_info['component'] == 'design_assets':
                    restore_manager.restore_design_assets(file_info['file'])
            
            print("復元が完了しました")
            
        except (ValueError, IndexError):
            print("無効な選択です")
            exit(1)
    
    else:
        # バックアップモード
        backup_manager = BackupManager()
        
        print("フルバックアップを開始します...")
        backup_info = backup_manager.create_full_backup()
        
        print(f"バックアップ完了: {backup_info['status']}")
        print("バックアップファイル:")
        for file_info in backup_info['files']:
            print(f"  {file_info['component']}: {file_info['file']} ({file_info['size_mb']} MB)")
        
        # 古いバックアップのクリーンアップ
        deleted = backup_manager.cleanup_old_backups()
        if deleted:
            print(f"古いバックアップファイル {len(deleted)} 個を削除しました")
```

### 8.4 パフォーマンス監視・最適化

#### パフォーマンス監視ダッシュボード
**scripts/performance_monitor.py**:
```python
#!/usr/bin/env python3
import time
import psutil
import sqlite3
import json
import requests
from datetime import datetime, timedelta
from collections import deque
import threading

class PerformanceMonitor:
    def __init__(self, interval=60):
        self.interval = interval
        self.running = False
        self.metrics_history = deque(maxlen=1440)  # 24時間分（1分間隔）
        
        self.current_metrics = {
            'timestamp': None,
            'cpu_percent': 0,
            'memory_percent': 0,
            'disk_usage_percent': 0,
            'api_response_time': 0,
            'database_connections': 0,
            'cache_hit_rate': 0,
            'active_tasks': 0
        }
    
    def collect_system_metrics(self):
        """システムメトリクスの収集"""
        # CPU使用率
        self.current_metrics['cpu_percent'] = psutil.cpu_percent(interval=1)
        
        # メモリ使用率
        memory = psutil.virtual_memory()
        self.current_metrics['memory_percent'] = memory.percent
        
        # ディスク使用率
        disk = psutil.disk_usage('.')
        self.current_metrics['disk_usage_percent'] = (disk.used / disk.total) * 100
        
        # ネットワーク統計
        net_io = psutil.net_io_counters()
        self.current_metrics['network_bytes_sent'] = net_io.bytes_sent
        self.current_metrics['network_bytes_recv'] = net_io.bytes_recv
    
    def check_api_performance(self):
        """API パフォーマンスチェック"""
        try:
            start_time = time.time()
            response = requests.get('http://localhost:5000/api/health', timeout=10)
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                self.current_metrics['api_response_time'] = response_time
                self.current_metrics['api_status'] = 'healthy'
            else:
                self.current_metrics['api_status'] = 'unhealthy'
                
        except Exception as e:
            self.current_metrics['api_response_time'] = 999
            self.current_metrics['api_status'] = 'error'
    
    def check_database_performance(self):
        """データベースパフォーマンスチェック"""
        try:
            start_time = time.time()
            
            conn = sqlite3.connect('data/database.db')
            cursor = conn.cursor()
            
            # 簡単なクエリでレスポンス時間測定
            cursor.execute("SELECT COUNT(*) FROM design_assets")
            asset_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM generated_presentations")
            presentation_count = cursor.fetchone()[0]
            
            query_time = time.time() - start_time
            
            conn.close()
            
            self.current_metrics['database_response_time'] = query_time
            self.current_metrics['database_asset_count'] = asset_count
            self.current_metrics['database_presentation_count'] = presentation_count
            
        except Exception as e:
            self.current_metrics['database_response_time'] = 999
            self.current_metrics['database_status'] = 'error'
    
    def check_cache_performance(self):
        """キャッシュパフォーマンスチェック"""
        try:
            # キャッシュ統計をAPIから取得
            response = requests.get('http://localhost:5000/api/cache/stats', timeout=5)
            if response.status_code == 200:
                cache_stats = response.json()
                self.current_metrics['cache_hit_rate'] = cache_stats.get('hit_rate_percent', 0)
                self.current_metrics['cache_size'] = cache_stats.get('memory_cache_size', 0)
            
        except Exception:
            self.current_metrics['cache_hit_rate'] = 0
    
    def check_background_tasks(self):
        """バックグラウンドタスクの監視"""
        try:
            response = requests.get('http://localhost:5000/api/tasks/stats', timeout=5)
            if response.status_code == 200:
                task_stats = response.json()
                self.current_metrics['active_tasks'] = task_stats.get('queue_size', 0)
                self.current_metrics['total_tasks'] = task_stats.get('total_tasks', 0)
            
        except Exception:
            self.current_metrics['active_tasks'] = 0
    
    def collect_all_metrics(self):
        """全メトリクスの収集"""
        self.current_metrics['timestamp'] = datetime.now().isoformat()
        
        self.collect_system_metrics()
        self.check_api_performance()
        self.check_database_performance()
        self.check_cache_performance()
        self.check_background_tasks()
        
        # 履歴に追加
        self.metrics_history.append(self.current_metrics.copy())
    
    def analyze_trends(self):
        """パフォーマンストレンドの分析"""
        if len(self.metrics_history) < 10:
            return None
        
        recent_metrics = list(self.metrics_history)[-10:]  # 過去10分
        
        analysis = {
            'avg_cpu': sum(m['cpu_percent'] for m in recent_metrics) / len(recent_metrics),
            'avg_memory': sum(m['memory_percent'] for m in recent_metrics) / len(recent_metrics),
            'avg_api_response_time': sum(m['api_response_time'] for m in recent_metrics) / len(recent_metrics),
            'avg_db_response_time': sum(m.get('database_response_time', 0) for m in recent_metrics) / len(recent_metrics)
        }
        
        # 異常検知
        alerts = []
        
        if analysis['avg_cpu'] > 80:
            alerts.append({'type': 'cpu_high', 'value': analysis['avg_cpu']})
        
        if analysis['avg_memory'] > 85:
            alerts.append({'type': 'memory_high', 'value': analysis['avg_memory']})
        
        if analysis['avg_api_response_time'] > 5:
            alerts.append({'type': 'api_slow', 'value': analysis['avg_api_response_time']})
        
        if analysis['avg_db_response_time'] > 1:
            alerts.append({'type': 'database_slow', 'value': analysis['avg_db_response_time']})
        
        return {
            'analysis': analysis,
            'alerts': alerts,
            'timestamp': datetime.now().isoformat()
        }
    
    def generate_performance_report(self):
        """パフォーマンスレポートの生成"""
        trends = self.analyze_trends()
        
        report = {
            'generated_at': datetime.now().isoformat(),
            'current_metrics': self.current_metrics,
            'trend_analysis': trends,
            'recommendations': []
        }
        
        # パフォーマンス改善の推奨事項
        if trends and trends['alerts']:
            for alert in trends['alerts']:
                if alert['type'] == 'cpu_high':
                    report['recommendations'].append({
                        'priority': 'high',
                        'issue': 'CPU使用率が高い',
                        'action': '不要なプロセスの停止、処理の最適化を検討してください'
                    })
                elif alert['type'] == 'memory_high':
                    report['recommendations'].append({
                        'priority': 'high',
                        'issue': 'メモリ使用率が高い',
                        'action': 'キャッシュクリアまたはシステム再起動を検討してください'
                    })
                elif alert['type'] == 'api_slow':
                    report['recommendations'].append({
                        'priority': 'medium',
                        'issue': 'API応答が遅い',
                        'action': 'OpenAI APIキー制限、ネットワーク接続を確認してください'
                    })
                elif alert['type'] == 'database_slow':
                    report['recommendations'].append({
                        'priority': 'medium',
                        'issue': 'データベース処理が遅い',
                        'action': 'データベースのVACUUM実行を検討してください'
                    })
        
        return report
    
    def save_report(self, report, filename=None):
        """レポートをファイルに保存"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"performance_report_{timestamp}.json"
        
        os.makedirs('reports', exist_ok=True)
        filepath = os.path.join('reports', filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        return filepath
    
    def start_monitoring(self):
        """監視開始"""
        self.running = True
        
        def monitor_loop():
            while self.running:
                self.collect_all_metrics()
                time.sleep(self.interval)
        
        monitor_thread = threading.Thread(target=monitor_loop)
        monitor_thread.daemon = True
        monitor_thread.start()
        
        print(f"パフォーマンス監視を開始しました (間隔: {self.interval}秒)")
    
    def stop_monitoring(self):
        """監視停止"""
        self.running = False
        print("パフォーマンス監視を停止しました")

# コマンドライン実行
if __name__ == "__main__":
    import sys
    
    monitor = PerformanceMonitor()
    
    if len(sys.argv) > 1 and sys.argv[1] == 'report':
        # 一回限りのレポート生成
        monitor.collect_all_metrics()
        report = monitor.generate_performance_report()
        
        print("=== パフォーマンスレポート ===")
        print(f"生成時刻: {report['generated_at']}")
        
        print(f"\n[現在のメトリクス]")
        for key, value in report['current_metrics'].items():
            if key != 'timestamp':
                print(f"  {key}: {value}")
        
        if report['trend_analysis'] and report['trend_analysis']['alerts']:
            print(f"\n[アラート]")
            for alert in report['trend_analysis']['alerts']:
                print(f"  {alert['type']}: {alert['value']}")
        
        if report['recommendations']:
            print(f"\n[推奨事項]")
            for rec in report['recommendations']:
                print(f"  [{rec['priority']}] {rec['issue']}")
                print(f"    → {rec['action']}")
        
        # レポート保存
        report_path = monitor.save_report(report)
        print(f"\nレポートを保存しました: {report_path}")
        
    else:
        # 継続監視モード
        try:
            monitor.start_monitoring()
            
            while True:
                time.sleep(10)
                
                # 10分ごとにレポート生成
                report = monitor.generate_performance_report()
                if report['trend_analysis'] and report['trend_analysis']['alerts']:
                    print(f"\n⚠️ アラート検出: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                    for alert in report['trend_analysis']['alerts']:
                        print(f"  {alert['type']}: {alert['value']}")
                
        except KeyboardInterrupt:
            monitor.stop_monitoring()
            print("\n監視を終了します")
```

これらの運用・保守手順により、システムの安定稼働と継続的な改善が可能になります。また、問題の早期発見と迅速な対応により、サービス品質を維持できます。

続いて、ユーザーマニュアルやトラブルシューティングガイドなど、さらに必要な部分があれば提供いたします。