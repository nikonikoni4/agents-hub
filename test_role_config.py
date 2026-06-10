from agents_hub.roles import RoleManager

rm = RoleManager()
config = rm.get_role("manager").get_role_config()
print(f"work_root: {config.work_root}")
print(f"bare: {config.bare}")
print(f"platform: {config.platform}")
