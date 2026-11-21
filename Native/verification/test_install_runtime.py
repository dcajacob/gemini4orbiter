"""Check a complete overlay and failures before and during installation."""
from importlib.util import module_from_spec, spec_from_file_location
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, main, mock

script = Path(__file__).resolve().parents[1] / "install-runtime.py"
spec = spec_from_file_location("install_runtime", script)
installer = module_from_spec(spec)
spec.loader.exec_module(installer)


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


class InstallerChecks(TestCase):
    def setUp(self):
        scratch = TemporaryDirectory()
        self.addCleanup(scratch.cleanup)
        root = Path(scratch.name)
        self.engine, self.addon, self.runtime = [root / name for name in ("engine", "addon", "runtime")]
        for name in installer.REQUIRED_ENGINE:
            write(self.engine / name, b"new engine product")
        for name in installer.REQUIRED_GEMINI:
            write(self.addon / name, b"new Gemini product")
        for name in ("engine/run-orbiter", "launch-orbiter", "resources/Config/Earth.cfg"):
            write(self.runtime / name, b"stock file")
        for name in ("celestial-data", "planet-archives"):
            (self.runtime / name).mkdir()

        self.old = self.runtime / "engine/orbiter-production"
        write(self.old, b"previous engine")
        self.stock = root / "stock-copy"
        os.link(self.old, self.stock)

    def test_complete_overlay_keeps_hardlinked_stock(self):
        installer.install(self.engine, self.addon, self.runtime)
        for name in installer.REQUIRED_ENGINE:
            self.assertEqual((self.runtime / "engine" / name).read_bytes(), b"new engine product")
        for name in installer.REQUIRED_GEMINI:
            self.assertEqual((self.runtime / "engine" / name).read_bytes(), b"new Gemini product")
        self.assertEqual(self.stock.read_bytes(), b"previous engine")

    def test_missing_inputs_leave_existing_files_alone(self):
        for parent, name in (
            (self.runtime, "resources/Config/Earth.cfg"),
            (self.engine, "NativeModules/Graphics/OGLClient.so"),
            (self.addon, "NativeModules/Vessel/GATV.so"),
        ):
            with self.subTest(path=name):
                path = parent / name
                content = path.read_bytes()
                path.unlink()
                with self.assertRaisesRegex(ValueError, "Missing or empty"):
                    installer.install(self.engine, self.addon, self.runtime)
                self.assertTrue(self.old.samefile(self.stock))
                self.assertFalse((self.runtime / "engine/liborbiter_production_vessels.so").exists())
                path.write_bytes(content)

    def test_failed_replacement_rolls_back(self):
        replace = Path.replace

        def fail_one_file(path, dest):
            if dest == self.runtime / "engine/NativeModules/Vessel/GATV.so":
                raise OSError("simulated installation failure")
            return replace(path, dest)

        with mock.patch.object(Path, "replace", fail_one_file), self.assertRaisesRegex(OSError, "simulated"):
            installer.install(self.engine, self.addon, self.runtime)
        self.assertTrue(self.old.samefile(self.stock))
        self.assertFalse((self.runtime / "engine/NativeModules/Graphics/OGLClient.so").exists())


if __name__ == "__main__":
    main()
