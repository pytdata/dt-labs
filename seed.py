import asyncio
from sqlalchemy import select

# Import your database and models
from app.db.session import AsyncSessionLocal
from app.models import User
from app.core.security import get_password_hash
from app.models.permission import Permission, Role


async def bootstrap_system():
    async with AsyncSessionLocal() as db:
        print("🚀 Starting System Bootstrap...")

        # 1. Create a "Global" Permission (or specifically for Settings)
        # For a superuser, we usually give them access to the 'settings' resource
        perm_stmt = select(Permission).where(
            Permission.resource == "settings", Permission.action == "write"
        )
        result = await db.execute(perm_stmt)
        admin_perm = result.scalar_one_or_none()

        if not admin_perm:
            admin_perm = Permission(resource="settings", action="write")
            db.add(admin_perm)
            await db.flush()
            print("✅ Created 'settings:write' permission.")

        # 2. Create the Admin Role
        role_stmt = select(Role).where(Role.slug == "admin")
        result = await db.execute(role_stmt)
        admin_role = result.scalar_one_or_none()

        if not admin_role:
            admin_role = Role(
                name="Super Administrator",
                slug="admin",
                description="Full system access and role management",
            )
            admin_role.permissions.append(admin_perm)
            db.add(admin_role)
            await db.flush()
            print("✅ Created 'admin' role.")

        # 3. Create/Update your User
        user_email = "admin@ykg.com"  # Change to your actual email
        user_stmt = select(User).where(User.email == user_email)
        result = await db.execute(user_stmt)
        user = result.scalar_one_or_none()

        if not user:
            user = User(
                email=user_email,
                full_name="System Admin",
                password_hash=get_password_hash("admin123"),  # Change this!
                role_id=admin_role.id,
                is_active=True,
            )
            db.add(user)
            print(f"✅ Created new Admin user: {user_email}")
        else:
            user.role_id = admin_role.id
            print(f"✅ Updated existing user {user_email} to Admin role.")

        await db.commit()
        print("⭐ Bootstrap Complete. You can now log in and manage roles.")


if __name__ == "__main__":
    asyncio.run(bootstrap_system())
