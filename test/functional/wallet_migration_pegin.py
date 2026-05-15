#!/usr/bin/env python3
# Copyright (c) 2024-present The Elements Project developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.
"""Test that migratewallet captures (fedpegscript, claim_script) pairs.

Spins up a parent (elementsregtest) + sidechain (elementsregtest, dynafed
activated from genesis) pair, creates a legacy BDB wallet on the sidechain,
performs pegin claims under (a) the initial fedpegscript and (b) a rotated
fedpegscript pushed via submitblock, then runs migratewallet and asserts
both per-pair log lines.

The data captured is in-memory only (MigrationData::pegin_scripts); this
test exercises the snapshot path that a follow-up PR will consume to build
pegin(...) descriptors.
"""

from test_framework.test_framework import BitcoinTestFramework
from test_framework.util import (
    assert_equal,
    find_vout_for_address,
    get_auth_cookie,
    get_datadir_path,
    p2p_port,
    rpc_port,
)
from test_framework import util


class WalletMigrationPeginTest(BitcoinTestFramework):
    def add_options(self, parser):
        self.add_wallet_options(parser, descriptors=False)

    def set_test_params(self):
        self.setup_clean_chain = True
        self.num_nodes = 2

    def skip_test_if_missing_module(self):
        self.skip_if_no_wallet()
        self.skip_if_no_bdb()

    def setup_network(self, split=False):
        self.nodes = []

        parent_chain = "elementsregtest"
        parent_args = [
            "-port=" + str(p2p_port(0)),
            "-rpcport=" + str(rpc_port(0)),
            "-validatepegin=0",
            "-initialfreecoins=0",
            "-anyonecanspendaremine=1",
            "-signblockscript=51",
        ]
        self.add_nodes(1, [parent_args], chain=[parent_chain])
        self.start_node(0)

        self.parentgenesisblockhash = self.nodes[0].getblockhash(0)
        parent_pegged_asset = self.nodes[0].getsidechaininfo()["pegged_asset"]

        self.fedpegscript = "512103dff4923d778550cc13ce0d887d737553b4b58f4e8e886507fc39f5e447b2186451ae"
        datadir = get_datadir_path(self.options.tmpdir, 0)
        rpc_u, rpc_p = get_auth_cookie(datadir, parent_chain)
        side_args = [
            "-printtoconsole=0",
            "-port=" + str(p2p_port(1)),
            "-rpcport=" + str(rpc_port(1)),
            "-validatepegin=1",
            "-fedpegscript=%s" % self.fedpegscript,
            "-minrelaytxfee=0",
            "-blockmintxfee=0",
            "-initialfreecoins=0",
            "-peginconfirmationdepth=10",
            "-mainchainrpchost=127.0.0.1",
            "-mainchainrpcport=%s" % rpc_port(0),
            "-mainchainrpcuser=%s" % rpc_u,
            "-mainchainrpcpassword=%s" % rpc_p,
            "-parentgenesisblockhash=%s" % self.parentgenesisblockhash,
            "-parentpubkeyprefix=235",
            "-parentscriptprefix=75",
            "-parent_bech32_hrp=ert",
            "-con_parent_chain_signblockscript=51",
            "-con_parent_pegged_asset=%s" % parent_pegged_asset,
            "-checkmempool=0",
            "-evbparams=dynafed:-1:::",  # dynafed active from first block
            "-deprecatedrpc=create_bdb",
        ]
        self.add_nodes(1, [side_args], chain=["elementsregtest"])
        self.start_node(1)

    def run_test(self):
        parent = self.nodes[0]
        sidechain = self.nodes[1]

        parent.importprivkey(privkey=parent.get_deterministic_priv_key().key, label="mining")
        sidechain.importprivkey(privkey=sidechain.get_deterministic_priv_key().key, label="mining")
        util.node_fastmerkle = sidechain

        self.generate(parent, 101, sync_fun=self.no_op)
        self.generate(sidechain, 101, sync_fun=self.no_op)

        wallet_name = "legacy_pegin"
        sidechain.createwallet(wallet_name=wallet_name, descriptors=False)
        legacy = sidechain.get_wallet_rpc(wallet_name)
        assert_equal(legacy.getwalletinfo()["descriptors"], False)
        assert_equal(legacy.getwalletinfo()["format"], "bdb")

        def do_pegin(amount):
            addrs = legacy.getpeginaddress()
            mainchain_addr = addrs["mainchain_address"]
            claim_script = addrs["claim_script"]
            txid = parent.sendtoaddress(mainchain_addr, amount)
            find_vout_for_address(parent, txid, mainchain_addr)
            self.generate(parent, 12, sync_fun=self.no_op)
            proof = parent.gettxoutproof([txid])
            raw = parent.gettransaction(txid)["hex"]
            pegtxid = legacy.claimpegin(raw, proof)
            self.generate(sidechain, 1, sync_fun=self.no_op)
            assert_equal(legacy.gettransaction(pegtxid, True, True)["confirmations"], 1)
            return claim_script

        self.log.info("Pegin #1 under the initial fedpegscript")
        fps1 = sidechain.getsidechaininfo()["current_fedpegscripts"][0]
        assert_equal(fps1, self.fedpegscript)
        claim1 = do_pegin(1)

        self.log.info("Rotate fedpegscript via dynafed submitblock loop")
        wsh_op_true = sidechain.decodescript("51")["segwit"]["hex"]
        tweaked = sidechain.tweakfedpegscript("deadbeef")
        new_fps = tweaked["script"]
        assert new_fps != fps1
        for _ in range(15):
            block_hex = sidechain.getnewblockhex(
                0,
                {
                    "signblockscript": wsh_op_true,
                    "max_block_witness": 10,
                    "fedpegscript": new_fps,
                    "extension_space": [],
                },
            )
            sidechain.submitblock(block_hex)
        current = sidechain.getsidechaininfo()["current_fedpegscripts"]
        assert new_fps in current, current
        assert fps1 in current, current

        self.log.info("Pegin #2 under the rotated fedpegscript")
        claim2 = do_pegin(2)
        assert claim1 != claim2

        # Add a non-pegin tx into mapWallet so the iteration loop in
        # DoMigration also exercises the `!m_is_pegin` skip branch.
        self.log.info("Add a non-pegin wallet tx to exercise the skip branch")
        non_pegin_addr = legacy.getnewaddress()
        non_pegin_txid = legacy.sendtoaddress(non_pegin_addr, 0.1)
        self.generate(sidechain, 1, sync_fun=self.no_op)
        assert_equal(legacy.gettransaction(non_pegin_txid)["confirmations"], 1)
        # mapWallet should now hold 3 entries (2 pegins + 1 self-send),
        # but only 2 of them produce pairs.
        assert_equal(len(legacy.listtransactions("*", 100)) >= 3, True)

        self.log.info("migratewallet: assert per-pair log content")
        expected_count = "Captured 2 (fedpegscript, claim_script) pair(s)"
        with sidechain.assert_debug_log(expected_msgs=[expected_count]):
            sidechain.migratewallet(wallet_name=wallet_name)

        debug_log = sidechain.debug_log_path.read_text()

        def matched_fps(claim_hex):
            for fps in current:
                line = "Pegin pair: fedpegscript=%s claim_script=%s" % (fps, claim_hex)
                if line in debug_log:
                    return fps
            return None

        m1 = matched_fps(claim1)
        m2 = matched_fps(claim2)
        assert m1 is not None, "no log line for claim1=%s" % claim1
        assert m2 is not None, "no log line for claim2=%s" % claim2
        self.log.info("claim1 paired with fps=%s" % m1)
        self.log.info("claim2 paired with fps=%s" % m2)
        # Distinct fedpegscripts across the rotation prove the resolver
        # loop after GetValidFedpegScripts is exercised end-to-end.
        assert m1 != m2, "expected distinct fedpegscripts across rotation (got %s, %s)" % (m1, m2)

        migrated = sidechain.get_wallet_rpc(wallet_name)
        assert_equal(migrated.getwalletinfo()["descriptors"], True)


if __name__ == "__main__":
    WalletMigrationPeginTest(__file__).main()
