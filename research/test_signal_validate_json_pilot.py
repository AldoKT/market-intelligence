"""Fail closed before recomputation or protected-file writes."""
import hashlib,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from research import signal_validate_json_pilot as pilot

class ValidationBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        root=Path(self.temporary.name)
        self.source=root/'source';self.source.mkdir()
        self.payloads=root/'payloads';self.payloads.mkdir()
        self.manifest={'methodology_version':'phase1-json-pilot-2.0','gate_d_approved':True,
                       'as_of':'2026-09-30','symbols':['ANTM','INCO','BBCA'],'source_sha256':{}}
        for name in ('daily','foreign_flow','broker_activity','broker_registry'):
            file=self.source/(name+'.json');file.write_text('[]',encoding='utf-8')
            self.manifest['source_sha256'][name]=hashlib.sha256(file.read_bytes()).hexdigest()
        self.save_manifest()

    def save_manifest(self):
        (self.payloads/'manifest.json').write_text(json.dumps(self.manifest),encoding='utf-8')

    def blocked(self,pattern):
        with patch.object(pilot,'detector_run') as recompute:
            with self.assertRaisesRegex(ValueError,pattern):pilot.validate(self.source,self.payloads)
            recompute.assert_not_called()

    def test_changed_source_stops_before_recompute(self):
        path=self.source/'daily.json';path.write_text('[{}]',encoding='utf-8')
        self.blocked('Source changed since Gate D')
        self.assertEqual(path.read_text(),'[{}]')

    def test_incomplete_manifest_cannot_skip_source_validation(self):
        self.manifest['source_sha256']={};self.save_manifest()
        self.blocked('exactly four')

    def test_unapproved_payloads_stop(self):
        self.manifest['gate_d_approved']=False;self.save_manifest()
        self.blocked('approved fixed')

    def test_wrong_snapshot_stops(self):
        self.manifest['as_of']='2026-10-06';self.save_manifest()
        self.blocked('fixed Sep30')

    def test_report_cannot_overwrite_source_or_payload(self):
        for target in (self.source/'daily.json',self.payloads/'manifest.json'):
            before=target.read_bytes()
            argv=['pilot','--source',str(self.source),'--payloads',str(self.payloads),'--report',str(target)]
            with patch('sys.argv',argv),patch.object(pilot,'validate') as validate:
                self.assertEqual(pilot.main(),1);validate.assert_not_called()
            self.assertEqual(target.read_bytes(),before)

if __name__=='__main__':unittest.main()
