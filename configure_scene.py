#!/usr/bin/env python3
"""
RAN Digital Twin Scene Configuration Manager

使用方式:
  python3 configure_scene.py --help
  python3 configure_scene.py building --name Building_1 --height 500
  python3 configure_scene.py gnb --name gNB_Macro_NW --height 500
  python3 configure_scene.py ue --name UE_1 --height 50 --speed 20
  python3 configure_scene.py list
  python3 configure_scene.py apply
"""

import json
import sys
import argparse
from pathlib import Path

CONFIG_FILE = Path(__file__).parent / "scene_config.json"

def load_config():
    """Load scene configuration"""
    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)

def save_config(config):
    """Save scene configuration (preserves file inode for Docker volume mount)"""
    # Write to temp file then move (sed-like behavior)
    temp_file = CONFIG_FILE.with_suffix('.json.tmp')
    with open(temp_file, 'w') as f:
        json.dump(config, f, indent=2)
    temp_file.replace(CONFIG_FILE)
    print(f"✓ 配置已保存到 {CONFIG_FILE}")

def list_objects(args):
    """List all configurable objects"""
    config = load_config()

    print("\n" + "="*60)
    print("RAN 數字孿生場景對象列表")
    print("="*60)

    # Buildings
    print("\n【Buildings】(3D Revit 建築)")
    for b in config.get('buildings', []):
        h = b.get('target_height_m', '未設定')
        pos = b.get('position', [0,0,0])
        print(f"  {b['name']:15} 高度: {h:>6}m  位置: {pos}")

    # Obstacles
    print("\n【Obstacles】(立方體障礙物)")
    for o in config.get('obstacles', []):
        size = o.get('size', [0,0,0])
        pos = o.get('position', [0,0,0])
        print(f"  {o['name']:15} 大小: {size}  位置: {pos}")

    # gNBs
    print("\n【gNBs】(基站塔)")
    for g in config.get('gnbs', []):
        h = g.get('target_height_m', '未設定')
        freq = g.get('frequency_ghz', '?')
        pos = g.get('position', [0,0,0])
        print(f"  {g['name']:20} 高度: {h:>6}m  頻率: {freq}GHz  位置: {pos}")

    # UEs
    print("\n【UEs】(用戶設備/角色)")
    for u in config.get('ues', []):
        h = u.get('target_height_m', 1.7)
        speed = u.get('speed_mps', 0)
        waypoints = len(u.get('waypoints', []))
        print(f"  {u['name']:20} 高度: {h:>6}m  速度: {speed:>4} m/s  路徑點: {waypoints}")

    print("\n" + "="*60 + "\n")

def update_building(args):
    """Update building configuration"""
    config = load_config()

    for b in config.get('buildings', []):
        if b['name'] == args.name:
            if args.height:
                b['target_height_m'] = args.height
            if args.position:
                b['position'] = args.position
            if args.color:
                b['color'] = args.color
            save_config(config)
            print(f"✓ {args.name} 已更新")
            return

    print(f"✗ 找不到建築: {args.name}")
    sys.exit(1)

def update_gnb(args):
    """Update gNB configuration"""
    config = load_config()

    for g in config.get('gnbs', []):
        if g['name'] == args.name:
            if args.height:
                g['target_height_m'] = args.height
            if args.power:
                g['power_dbm'] = args.power
            if args.frequency:
                g['frequency_ghz'] = args.frequency
            if args.bandwidth:
                g['bandwidth_mhz'] = args.bandwidth
            save_config(config)
            print(f"✓ {args.name} 已更新")
            return

    print(f"✗ 找不到基站: {args.name}")
    sys.exit(1)

def update_ue(args):
    """Update UE configuration"""
    config = load_config()

    for u in config.get('ues', []):
        if u['name'] == args.name:
            if args.height:
                u['target_height_m'] = args.height
            if args.speed is not None:
                u['speed_mps'] = args.speed
            if args.position:
                u['position'] = args.position
            save_config(config)
            print(f"✓ {args.name} 已更新")
            return

    print(f"✗ 找不到UE: {args.name}")
    sys.exit(1)

def apply_changes(args):
    """Apply changes to running scene"""
    print("\n執行以下操作:")
    print("1. 清除 Kit 緩存...")
    import subprocess
    result = subprocess.run(
        ["docker", "exec", "omniver_kit", "rm", "-rf", "/root/.local/share/ov/data/Kit/ran_server"],
        capture_output=True
    )
    if result.returncode == 0:
        print("   ✓ 緩存已清除")

    print("2. 重建場景...")
    result = subprocess.run(
        ["curl", "-s", "-X", "POST", "http://localhost:8080/scene/build"],
        capture_output=True, text=True
    )
    if "queued" in result.stdout:
        print("   ✓ 場景重建已排隊")
        print("\n等待 10 秒讓場景加載...")
        import time
        time.sleep(10)
        print("✓ 完成！檢查 VNC 查看變更")
    else:
        print("   ✗ 失敗，請檢查 Kit 服務是否運行")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(
        description="RAN 數字孿生場景配置工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  列表所有對象:
    python3 configure_scene.py list

  調整 Building_1 高度為 500m:
    python3 configure_scene.py building --name Building_1 --height 500

  調整 gNB 高度和功率:
    python3 configure_scene.py gnb --name gNB_Macro_NW --height 600 --power 45

  調整 UE 速度:
    python3 configure_scene.py ue --name UE_1 --speed 15

  應用所有變更到運行中的場景:
    python3 configure_scene.py apply
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='命令')

    # list command
    subparsers.add_parser('list', help='列表所有對象')

    # building command
    building_parser = subparsers.add_parser('building', help='調整建築配置')
    building_parser.add_argument('--name', required=True, help='建築名稱 (Building_1, Building_2)')
    building_parser.add_argument('--height', type=float, help='目標高度 (米)')
    building_parser.add_argument('--position', type=float, nargs=3, help='位置 [x y z]')
    building_parser.add_argument('--color', type=float, nargs=3, help='顏色 [R G B]')

    # gnb command
    gnb_parser = subparsers.add_parser('gnb', help='調整基站配置')
    gnb_parser.add_argument('--name', required=True, help='基站名稱')
    gnb_parser.add_argument('--height', type=float, help='目標高度 (米)')
    gnb_parser.add_argument('--power', type=float, help='功率 (dBm)')
    gnb_parser.add_argument('--frequency', type=float, help='頻率 (GHz)')
    gnb_parser.add_argument('--bandwidth', type=float, help='帶寬 (MHz)')

    # ue command
    ue_parser = subparsers.add_parser('ue', help='調整UE配置')
    ue_parser.add_argument('--name', required=True, help='UE名稱')
    ue_parser.add_argument('--height', type=float, help='目標身高 (米)')
    ue_parser.add_argument('--speed', type=float, help='移動速度 (m/s)')
    ue_parser.add_argument('--position', type=float, nargs=3, help='位置 [x y z]')

    # apply command
    subparsers.add_parser('apply', help='應用變更到運行中的場景')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    if args.command == 'list':
        list_objects(args)
    elif args.command == 'building':
        update_building(args)
    elif args.command == 'gnb':
        update_gnb(args)
    elif args.command == 'ue':
        update_ue(args)
    elif args.command == 'apply':
        apply_changes(args)

if __name__ == '__main__':
    main()
