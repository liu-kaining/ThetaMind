#!/usr/bin/env python3
"""
Script to set a user as superuser.
Usage: python set_superuser.py <email>
"""

import asyncio
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.models import User


async def set_superuser(email: str):
    """Set a user as superuser by email."""
    
    # Create async engine
    engine = create_async_engine(
        settings.database_url,
        echo=False,
    )
    
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        try:
            # Find user by email
            result = await session.execute(
                select(User).where(User.email == email)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                print(f"❌ User with email '{email}' not found")
                print("\nAvailable users:")
                all_users = await session.execute(select(User))
                users = all_users.scalars().all()
                if users:
                    for u in users:
                        print(f"  - {u.email} (superuser: {u.is_superuser})")
                else:
                    print("  No users found in database")
                return False
            
            if user.is_superuser:
                print(f"✅ User '{email}' is already a superuser")
                return True
            
            # Set as superuser
            user.is_superuser = True
            await session.commit()
            
            print(f"✅ Successfully set user '{email}' as superuser")
            return True
            
        except Exception as e:
            await session.rollback()
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            await engine.dispose()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python set_superuser.py <email>")
        print("\nExample:")
        print("  python set_superuser.py admin@example.com")
        sys.exit(1)
    
    email = sys.argv[1]
    
    try:
        success = asyncio.run(set_superuser(email))
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n❌ Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

