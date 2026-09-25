import os
import subprocess
import unittest

from scripts.host_tool_environment import host_tool_environment


class TestHostTools(unittest.TestCase):
    def test_preserves_parent_and_user_paths(self):
        parent = dict(PATH='/user/tools', LD_LIBRARY_PATH='/python/lib', LD_PRELOAD='/python/lib/custom.so',
                      HTTPS_PROXY='http://example.invalid:8080')
        clean = host_tool_environment(parent)
        self.assertEqual(parent['LD_LIBRARY_PATH'], '/python/lib')
        self.assertNotIn('LD_LIBRARY_PATH', clean)
        self.assertNotIn('LD_PRELOAD', clean)
        self.assertTrue(clean['PATH'].endswith('/user/tools'))
        self.assertEqual(clean['HTTPS_PROXY'], parent['HTTPS_PROXY'])

    def test_real_host_executables_with_contaminated_parent(self):
        parent = dict(os.environ, LD_LIBRARY_PATH='/home/agiuser/miniconda3/envs/artgym/lib',
                      LD_PRELOAD='/nonexistent/python-runtime-library.so')
        for command in [['ssh', '-V'], ['rsync', '--version'], ['curl', '--version']]:
            result = subprocess.run(command, env=host_tool_environment(parent), text=True,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
            self.assertEqual(result.returncode, 0, (command, result.stderr))
            self.assertNotIn('OpenSSL version mismatch', result.stderr)
            self.assertNotIn('cannot be preloaded', result.stderr)


if __name__ == '__main__':
    unittest.main()
