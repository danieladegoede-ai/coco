"""Provenance, architecture and exact test-coverage release gates."""
from __future__ import annotations
import hashlib,json,struct,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from tools.build_native import binary_identity
from tools.assemble_release import validate_artifacts


class NativeIdentityTests(unittest.TestCase):
    def identify(self,data):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'binary';p.write_bytes(data);return binary_identity(p)
    def test_windows_x64(self):
        data=bytearray(256);data[:2]=b'MZ';struct.pack_into('<I',data,0x3c,128);data[128:132]=b'PE\0\0';struct.pack_into('<H',data,132,0x8664)
        self.assertEqual(self.identify(data),('windows','x86_64'))
    def test_linux_x64(self):
        data=bytearray(64);data[:6]=b'\x7fELF\x02\x01';struct.pack_into('<H',data,18,62)
        self.assertEqual(self.identify(data),('linux','x86_64'))
    def test_macos_arm64(self):
        data=bytearray(32);data[:4]=b'\xcf\xfa\xed\xfe';struct.pack_into('<I',data,4,0x100000c)
        self.assertEqual(self.identify(data),('macos','arm64'))
    def test_unknown_is_not_native(self):
        with self.assertRaises(ValueError):self.identify(b'#!/usr/bin/env python3\n')
    def test_elf32_is_rejected(self):
        with self.assertRaises(ValueError):self.identify(b'\x7fELF\x01\x01'+b'\0'*60)
    def test_mz_without_pe_is_rejected(self):
        data=bytearray(128);data[:2]=b'MZ';struct.pack_into('<I',data,0x3c,64)
        with self.assertRaises(ValueError):self.identify(data)


class ReleaseEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        from tests.edge5000.cases import CASES
        for platform in ('windows','linux','macos'):
            directory=self.root/f'native-{platform}';directory.mkdir()
            filename='group-2.exe' if platform=='windows' else 'group-2';binary=directory/filename;binary.write_bytes(platform.encode())
            digest=hashlib.sha256(binary.read_bytes()).hexdigest()
            self.write(directory/'build-manifest.json',{'dirty':False,'source_commit':'commit','os':platform,'sha256':digest})
            self.write(directory/'acceptance.json',{'passed':True,'executable_sha256':digest})
            for shard in range(4):
                path=self.root/f'package-evidence-{platform}-{shard}'/f'package-{platform}-{shard}.json'
                self.write(path,{'passed':True,'executable_sha256':digest,'shard_count':4,'shard_index':shard,
                    'results':[{'id':c.case_id,'passed':True,'skipped':[],'run':1} for i,c in enumerate(CASES) if i%4==shard]})
        self.write(self.root/'gcc13-evidence/gcc13.json',{'g++13':{'reports':[{'passed':True}]},'gcc13':{'reports':[{'passed':True}]}})
        self.write(self.root/'user-manual/manual-manifest.json',{'source_commit':'commit','pages':5})
    def write(self,path,data):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(data))
    def change(self,path,fn):
        data=json.loads(path.read_text());fn(data);self.write(path,data)
    def test_complete_evidence_is_accepted(self):self.assertEqual(set(validate_artifacts(self.root,'commit')),{'windows','linux','macos'})
    def test_binary_tamper_is_rejected(self):
        (self.root/'native-windows/group-2.exe').write_bytes(b'tampered')
        with self.assertRaises(ValueError):validate_artifacts(self.root,'commit')
    def test_dirty_build_is_rejected(self):
        self.change(self.root/'native-linux/build-manifest.json',lambda d:d.update(dirty=True))
        with self.assertRaises(ValueError):validate_artifacts(self.root,'commit')
    def test_wrong_commit_is_rejected(self):
        with self.assertRaises(ValueError):validate_artifacts(self.root,'other')
    def test_missing_case_is_rejected(self):
        self.change(self.root/'package-evidence-linux-0/package-linux-0.json',lambda d:d['results'].pop())
        with self.assertRaises(ValueError):validate_artifacts(self.root,'commit')
    def test_duplicate_case_is_rejected(self):
        def duplicate(d):d['results'][1]=dict(d['results'][0])
        self.change(self.root/'package-evidence-linux-0/package-linux-0.json',duplicate)
        with self.assertRaises(ValueError):validate_artifacts(self.root,'commit')
    def test_skipped_case_is_rejected(self):
        self.change(self.root/'package-evidence-macos-1/package-macos-1.json',lambda d:d['results'][0].update(skipped=['not run']))
        with self.assertRaises(ValueError):validate_artifacts(self.root,'commit')
    def test_wrong_binary_test_hash_is_rejected(self):
        self.change(self.root/'package-evidence-windows-3/package-windows-3.json',lambda d:d.update(executable_sha256='wrong'))
        with self.assertRaises(ValueError):validate_artifacts(self.root,'commit')
    def test_failed_gcc_gate_is_rejected(self):
        self.change(self.root/'gcc13-evidence/gcc13.json',lambda d:d['gcc13']['reports'][0].update(passed=False))
        with self.assertRaises(ValueError):validate_artifacts(self.root,'commit')
    def test_manual_wrong_commit_is_rejected(self):
        self.change(self.root/'user-manual/manual-manifest.json',lambda d:d.update(source_commit='old'))
        with self.assertRaises(ValueError):validate_artifacts(self.root,'commit')
