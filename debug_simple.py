from app.View.BladeEngine import BladeEngine

content = "@cannot('delete-post')"

engine = BladeEngine(['/tmp'], debug=True)

# Test the specific directive
result = engine._cannot_directive("'delete-post'")
print("Cannot directive result:", result)

# Test compilation
compiled = engine.compile_blade(content)
print("Compiled:", compiled)