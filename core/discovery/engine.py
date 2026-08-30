import os
from pathlib import Path
from core.discovery.environment import ProjectEnvironment, DiscoveryEvidence

class DiscoveryEngine:
    def __init__(self, root: str | Path):
        self.root = Path(root).expanduser().resolve()
        
    def discover(self) -> ProjectEnvironment:
        env = ProjectEnvironment(root=str(self.root))
        
        self._detect_python(env)
        self._detect_node(env)
        self._detect_php(env)
        self._detect_android(env)
        self._detect_structure(env)
        
        return env
        
    def _detect_python(self, env: ProjectEnvironment):
        pyproject = self.root / "pyproject.toml"
        pytest_ini = self.root / "pytest.ini"
        req = self.root / "requirements.txt"
        
        if pyproject.exists() or pytest_ini.exists() or req.exists():
            env.languages["Python"] = DiscoveryEvidence("Python", "filesystem", "high")
            
        if pytest_ini.exists():
            if not env.test_runner: env.test_runner = []
            env.test_runner.append(DiscoveryEvidence("pytest", "pytest.ini", "high"))
            env.commands["test"].append(DiscoveryEvidence(f"PYTHONPATH=\"{env.root}\" pytest tests/", "pytest.ini", "high"))
        elif pyproject.exists():
            # might have pytest config inside
            content = pyproject.read_text(encoding="utf-8")
            if "pytest" in content:
                if not env.test_runner: env.test_runner = []
                env.test_runner.append(DiscoveryEvidence("pytest", "pyproject.toml", "medium"))
                env.commands["test"].append(DiscoveryEvidence(f"PYTHONPATH=\"{env.root}\" pytest tests/", "pyproject.toml", "medium"))
        
        if req.exists():
            content = req.read_text(encoding="utf-8")
            if "Flask" in content:
                env.frameworks["Flask"] = DiscoveryEvidence("Flask", "requirements.txt", "high")
                env.backend = DiscoveryEvidence("Flask", "requirements.txt", "high")
                
    def _detect_node(self, env: ProjectEnvironment):
        pkg = self.root / "package.json"
        if pkg.exists():
            env.languages["JavaScript"] = DiscoveryEvidence("JavaScript/TypeScript", "package.json", "high")
            env.package_managers["npm"] = DiscoveryEvidence("npm/yarn/pnpm", "package.json", "high")
            
            vite_conf = self.root / "vite.config.js"
            vite_conf_ts = self.root / "vite.config.ts"
            if vite_conf.exists() or vite_conf_ts.exists():
                if not env.build_system: env.build_system = []
                env.build_system.append(DiscoveryEvidence("Vite", "vite.config", "high"))
                
            try:
                import json
                data = json.loads(pkg.read_text(encoding="utf-8"))
                scripts = data.get("scripts", {})
                
                # Check scripts
                if "test" in scripts:
                    env.commands["test"].append(DiscoveryEvidence("npm test", "package.json scripts", "high"))
                    if not env.test_runner: env.test_runner = []
                    env.test_runner.append(DiscoveryEvidence("npm scripts", "package.json scripts", "high"))
                    if "vitest" in scripts["test"]:
                        env.test_runner.append(DiscoveryEvidence("vitest", "package.json scripts", "high"))
                    if "jest" in scripts["test"]:
                        env.test_runner.append(DiscoveryEvidence("jest", "package.json scripts", "high"))
                if "build" in scripts:
                    env.commands["build"].append(DiscoveryEvidence("npm run build", "package.json scripts", "high"))
                if "dev" in scripts:
                    env.commands["dev"].append(DiscoveryEvidence("npm run dev", "package.json scripts", "high"))
                if "lint" in scripts:
                    env.commands["lint"].append(DiscoveryEvidence("npm run lint", "package.json scripts", "high"))
                    
                deps = data.get("dependencies", {})
                dev_deps = data.get("devDependencies", {})
                if "jest" in dev_deps or "jest" in deps:
                    if not env.test_runner: env.test_runner = []
                    env.test_runner.append(DiscoveryEvidence("jest", "package.json dependencies", "high"))
            except Exception:
                pass

    def _detect_php(self, env: ProjectEnvironment):
        composer = self.root / "composer.json"
        artisan = self.root / "artisan"
        phpunit = self.root / "phpunit.xml"
        
        if composer.exists():
            env.languages["PHP"] = DiscoveryEvidence("PHP", "composer.json", "high")
            env.package_managers["Composer"] = DiscoveryEvidence("Composer", "composer.json", "high")
            
        if artisan.exists():
            env.frameworks["Laravel"] = DiscoveryEvidence("Laravel", "artisan", "high")
            env.backend = DiscoveryEvidence("Laravel", "artisan", "high")
            
        if phpunit.exists():
            if not env.test_runner: env.test_runner = []
            env.test_runner.append(DiscoveryEvidence("PHPUnit/Pest", "phpunit.xml", "high"))
            if artisan.exists():
                env.commands["test"].append(DiscoveryEvidence("php artisan test", "artisan + phpunit.xml", "high"))
            else:
                env.commands["test"].append(DiscoveryEvidence("vendor/bin/phpunit", "phpunit.xml", "medium"))

    def _detect_android(self, env: ProjectEnvironment):
        settings_gradle = self.root / "settings.gradle"
        settings_gradle_kts = self.root / "settings.gradle.kts"
        build_gradle = self.root / "build.gradle"
        
        if settings_gradle.exists() or settings_gradle_kts.exists() or build_gradle.exists():
            env.languages["Java/Kotlin"] = DiscoveryEvidence("Java/Kotlin", "gradle", "high")
            if not env.build_system: env.build_system = []
            env.build_system.append(DiscoveryEvidence("Gradle", "gradle file", "high"))
            
        app_manifest = self.root / "app" / "src" / "main" / "AndroidManifest.xml"
        if app_manifest.exists() or (self.root / "AndroidManifest.xml").exists():
            env.frameworks["Android"] = DiscoveryEvidence("Android", "AndroidManifest.xml", "high")
            env.commands["test"].append(DiscoveryEvidence("./gradlew test", "gradlew", "high"))
            env.commands["build"].append(DiscoveryEvidence("./gradlew assembleDebug", "gradlew", "high"))

    def _detect_structure(self, env: ProjectEnvironment):
        # Map well-known directories if they exist
        known_dirs = {
            "src": "source",
            "app": "application",
            "api": "api",
            "backend": "backend",
            "frontend": "frontend",
            "client": "client",
            "server": "server",
            "tests": "tests",
            "test": "tests",
            "spec": "tests",
            "docs": "documentation",
            "config": "configuration",
            "routes": "routes",
            "controllers": "controllers",
            "models": "models",
            "services": "services",
            "components": "components",
            "modules": "modules",
            "packages": "packages",
        }
        
        for d, role in known_dirs.items():
            if (self.root / d).is_dir():
                env.important_directories.append({
                    "path": d,
                    "role": role,
                    "source": "filesystem",
                    "confidence": "high"
                })
        
        # Detected modules -> peek into modules/ or app/
        if (self.root / "modules").is_dir():
            for child in (self.root / "modules").iterdir():
                if child.is_dir() and not child.name.startswith("__"):
                    env.detected_modules.append({
                        "path": f"modules/{child.name}",
                        "name": child.name,
                        "source": "filesystem",
                        "confidence": "medium"
                    })
