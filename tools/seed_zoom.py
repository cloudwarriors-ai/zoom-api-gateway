#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'app'))

from utils.provider_manager import get_provider_manager
import argparse

ZOOM_CONFIG = {
    "api_key": os.getenv("ZOOM_API_KEY", ""),
    "api_secret": os.getenv("ZOOM_API_SECRET", ""),
    "api_base_url": "https://api.zoom.us/v2"
}


def seed_zoom_provider(pm, tenant_id: str):
    """Seed Zoom provider credentials into Redis."""

    if not ZOOM_CONFIG['api_key'] or not ZOOM_CONFIG['api_secret']:
        print("❌ ZOOM_API_KEY and ZOOM_API_SECRET environment variables required")
        print("   Set them in .env or export them before running this script")
        return False

    print(f"🔐 Seeding Zoom provider credentials...")

    provider_config = {
        'status': 'active',
        'auth_type': 'api_key',
        'api_key': ZOOM_CONFIG['api_key'],
        'api_secret': ZOOM_CONFIG['api_secret'],
        'account_id': '',
        'api_base_url': ZOOM_CONFIG['api_base_url'],
        'rate_limit_window': '60',
        'rate_limit_calls': '40',
        'features_enabled': ['meetings', 'webinars', 'users', 'recordings']
    }

    print(f"🌱 Seeding Zoom provider for tenant={tenant_id}...")

    existing = pm.get_provider(tenant_id, 'zoom')

    if existing:
        print(f"⚠️  Zoom provider already exists, updating...")
        result = pm.update_provider(tenant_id, 'zoom', provider_config)
    else:
        result = pm.add_provider(tenant_id, 'zoom', provider_config)

    if result:
        print(f"✅ Zoom provider seeded successfully")
        provider = pm.get_provider(tenant_id, 'zoom')
        print(f"   Auth Type: {provider.get('auth_type')}")
        print(f"   API Base: {provider.get('api_base_url')}")
        print(f"   Rate Limit: {provider.get('rate_limit_calls')} calls/{provider.get('rate_limit_window')}s")
    else:
        print(f"❌ Failed to seed Zoom provider")

    return result


def seed_system_credentials(pm, tenant: str, app: str):
    """Seed system credentials into Redis."""
    print(f"🌱 Seeding system credentials: tenant={tenant} app={app}")

    system_config = {
        'client_id': ZOOM_CONFIG['api_key'],
        'client_secret': ZOOM_CONFIG['api_secret'],
        'auth_url': 'https://zoom.us/oauth/authorize',
        'token_url': 'https://zoom.us/oauth/token'
    }

    existing = pm.get_system_credentials(tenant, app)

    if existing:
        print(f"⚠️  System credentials already exist, updating...")
        result = pm.update_system_credentials(tenant, app, system_config)
    else:
        result = pm.add_system_credentials(tenant, app, system_config)

    if result:
        print(f"✅ System credentials seeded successfully")
    else:
        print(f"❌ Failed to seed system credentials")

    return result


def seed_tenant_config(pm, tenant: str):
    """Seed tenant configuration into Redis."""
    print(f"🌱 Seeding tenant config: tenant={tenant}")

    tenant_config = {
        'name': 'Cloud Warriors',
        'primary_provider': 'zoom',
        'sync_strategy': 'primary',
        'data_retention_days': 90,
        'timezone': 'America/New_York'
    }

    result = pm.set_tenant_config(tenant, tenant_config)

    if result:
        print(f"✅ Tenant config seeded successfully")
        config = pm.get_tenant_config(tenant)
        print(f"   Name: {config.get('name')}")
        print(f"   Primary Provider: {config.get('primary_provider')}")
    else:
        print(f"❌ Failed to seed tenant config")

    return result


def verify_redis_connection(pm):
    """Verify Redis connection is working."""
    try:
        pm.redis_client.ping()
        redis_host = os.getenv('REDIS_HOST', 'localhost')
        redis_port = os.getenv('REDIS_PORT', '6379')
        print(f"✅ Redis connection successful (connected to {redis_host}:{redis_port})")
        return True
    except Exception as e:
        redis_host = os.getenv('REDIS_HOST', 'localhost')
        redis_port = os.getenv('REDIS_PORT', '6379')
        print(f"❌ Redis connection failed: {e}")
        print(f"   Trying to connect to {redis_host}:{redis_port}")
        print("   Make sure Redis is running and accessible")
        return False


def main():
    parser = argparse.ArgumentParser(description='Seed Zoom credentials into Redis')
    parser.add_argument('--tenant', default='cloudwarriors', help='Tenant ID')
    parser.add_argument('--app', default='zoom', help='Application ID')
    parser.add_argument('--clean', action='store_true', help='Remove existing data first')

    args = parser.parse_args()

    print("=" * 70)
    print("Zoom Redis Seeding Script")
    print("=" * 70)

    pm = get_provider_manager()

    if not verify_redis_connection(pm):
        return 1

    if args.clean:
        print(f"\n🧹 Cleaning existing data...")
        pm.delete_provider(args.tenant, 'zoom')
        pm.delete_system_credentials(args.tenant, args.app)
        print(f"✅ Cleanup complete\n")

    print(f"\nSeeding Zoom for tenant={args.tenant} app={args.app}\n")

    success = True
    success &= seed_tenant_config(pm, args.tenant)
    success &= seed_system_credentials(pm, args.tenant, args.app)
    success &= seed_zoom_provider(pm, args.tenant)

    print("\n" + "=" * 70)
    if success:
        print("✅ All data seeded successfully!")
        print("\nNext steps:")
        print(f"  1. Start the API: python app/main.py")
        print(f"  2. Test health: curl http://localhost:8093/health")
        print(f"  3. Create session: curl -X POST -H 'Content-Type: application/json' \\")
        print(f"     -d '{{\"tenant\":\"{args.tenant}\",\"app\":\"{args.app}\"}}' \\")
        print(f"     http://localhost:8093/auth/connect")
        print(f"  4. Check status: curl 'http://localhost:8093/auth/status?tenant_id={args.tenant}'")
    else:
        print("❌ Some operations failed. Check errors above.")
    print("=" * 70)

    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
