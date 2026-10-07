import hashlib,json,tempfile,unittest,zipfile
from pathlib import Path
from research.signal_restore_checkpoint import restore

class RestoreCheckpointTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.folder=self.root/'research/data/checkpoints/phase2_expansion28';self.folder.mkdir(parents=True)
    def seed(self,relative='expansion_2026/daily.json'):
        data=b'[1]';archive=self.folder/'data.zip'
        with zipfile.ZipFile(archive,'w') as z:z.writestr(relative,data)
        manifest={'archives':[{'archive':'data.zip','sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'files':{relative:{'size':len(data),'sha256':hashlib.sha256(data).hexdigest()}}}]}
        (self.folder/'manifest.json').write_text(json.dumps(manifest))
        return self.root/'research/data/rework_phase1_v2/raw'/relative
    def test_roundtrip_and_second_restore_does_not_write(self):
        target=self.seed();self.assertEqual(restore(self.root,True)['files_restored'],0);self.assertFalse(target.exists())
        self.assertEqual(restore(self.root)['files_restored'],1)
        self.assertEqual(target.read_bytes(),b'[1]');self.assertEqual(restore(self.root)['files_restored'],0)
    def test_different_existing_file_is_preserved(self):
        target=self.seed();target.parent.mkdir(parents=True);target.write_bytes(b'[2]')
        with self.assertRaises(ValueError):restore(self.root)
        self.assertEqual(target.read_bytes(),b'[2]')
    def test_path_traversal_is_rejected_before_write(self):
        self.seed('../escape.json')
        with self.assertRaises(ValueError):restore(self.root)
        self.assertFalse((self.root/'research/data/rework_phase1_v2/escape.json').exists())
