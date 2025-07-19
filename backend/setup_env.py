#!/usr/bin/env python3
"""
Setup script for creating and configuring the virtual environment.
"""
import subprocess
import sys
import os
from pathlib import Path

def run_command(command, cwd=None):
    """Run a command and return the result."""
    try:
        result = subprocess.run(command, shell=True, cwd=cwd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Error running command: {command}")
            print(f"Error output: {result.stderr}")
            return False
        print(result.stdout)
        return True
    except Exception as e:
        print(f"Exception running command {command}: {e}")
        return False

def main():
    """Main setup function."""
    backend_dir = Path(__file__).parent
    venv_path = backend_dir / "venv"
    
    print("🚀 Setting up PromptFlow AI Backend Environment")
    print("=" * 50)
    
    # Check if virtual environment already exists
    if venv_path.exists():
        print(f"✅ Virtual environment already exists at: {venv_path}")
        activate_script = venv_path / "Scripts" / "activate.bat" if os.name == 'nt' else venv_path / "bin" / "activate"
        print(f"To activate it, run: {activate_script}")
        return
    
    # Create virtual environment
    print("📦 Creating virtual environment...")
    if not run_command(f"python -m venv venv", cwd=backend_dir):
        print("❌ Failed to create virtual environment")
        return
    
    print("✅ Virtual environment created successfully!")
    
    # Determine activation command based on OS
    if os.name == 'nt':  # Windows
        activate_cmd = str(venv_path / "Scripts" / "activate.bat")
        pip_cmd = str(venv_path / "Scripts" / "pip.exe")
    else:  # Unix/Linux/macOS
        activate_cmd = f"source {venv_path / 'bin' / 'activate'}"
        pip_cmd = str(venv_path / "bin" / "pip")
    
    print(f"📋 To activate the virtual environment, run:")
    print(f"   {activate_cmd}")
    print()
    
    # Install dependencies
    print("📦 Installing dependencies...")
    requirements_file = backend_dir / "requirements.txt"
    
    if requirements_file.exists():
        install_cmd = f'"{pip_cmd}" install -r requirements.txt'
        if run_command(install_cmd, cwd=backend_dir):
            print("✅ Dependencies installed successfully!")
        else:
            print("❌ Failed to install dependencies")
            print("You can install them manually after activating the environment:")
            print(f"   {activate_cmd}")
            print(f"   pip install -r requirements.txt")
    else:
        print("⚠️  requirements.txt not found, skipping dependency installation")
    
    print()
    print("🎉 Setup complete!")
    print()
    print("Next steps:")
    print(f"1. Activate the virtual environment: {activate_cmd}")
    print("2. Set up your .env file with Supabase credentials")
    print("3. Run database initialization: python scripts/init_db.py")
    print("4. Start the server: uvicorn app.main:app --reload")

if __name__ == "__main__":
    main()