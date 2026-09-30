import { useEffect, useState } from 'react';
import { verifyMessage } from 'viem';

interface Provider {
  isMetaMask?: boolean;
  request(args:{method:string;params?:unknown[]}):Promise<unknown>;
  on?(event:string,handler:(value:unknown)=>void):void;
  removeListener?(event:string,handler:(value:unknown)=>void):void;
}
declare global { interface Window { ethereum?: Provider } }

export function useWallet() {
  const [address,setAddress] = useState<`0x${string}`|null>(null);
  const [chainId,setChainId] = useState<number|null>(null);
  const [signedIn,setSignedIn] = useState(false);
  const [busy,setBusy] = useState(false);
  const [error,setError] = useState('');
  const available = typeof window !== 'undefined' && Boolean(window.ethereum);

  useEffect(() => {
    const provider=window.ethereum;
    if(!provider)return;
    const accountsChanged=(value:unknown)=>{
      const accounts=Array.isArray(value)?value:[];
      setAddress(typeof accounts[0]==='string' ? accounts[0] as `0x${string}` : null);
      setSignedIn(false);
    };
    const chainChanged=(value:unknown)=>{
      setChainId(typeof value==='string'?Number.parseInt(value,16):null);
      setSignedIn(false);
    };
    provider.on?.('accountsChanged',accountsChanged);provider.on?.('chainChanged',chainChanged);
    return()=>{provider.removeListener?.('accountsChanged',accountsChanged);provider.removeListener?.('chainChanged',chainChanged);};
  },[]);

  const connect=async()=>{
    if(!window.ethereum){setError('MetaMask was not detected. Install it or open this site inside a wallet browser.');return;}
    setBusy(true);setError('');
    try{
      const accounts=await window.ethereum.request({method:'eth_requestAccounts'});
      const id=await window.ethereum.request({method:'eth_chainId'});
      if(!Array.isArray(accounts)||typeof accounts[0]!=='string')throw new Error('No account was returned by the wallet.');
      setAddress(accounts[0] as `0x${string}`);setChainId(Number.parseInt(String(id),16));setSignedIn(false);
    }catch(e){setError(e instanceof Error?e.message:'Wallet connection was cancelled.');}
    finally{setBusy(false);}
  };

  const signIn=async()=>{
    if(!window.ethereum||!address||!chainId)return;
    setBusy(true);setError('');
    try{
      const nonce=Array.from(crypto.getRandomValues(new Uint8Array(8)),x=>x.toString(16).padStart(2,'0')).join('');
      const issued=new Date(), expires=new Date(issued.getTime()+10*60_000);
      const message=`${location.host} wants you to sign in with your Ethereum account:\n${address}\n\nVerify your wallet for this Stock Scout Studio preview. This signature does not spend funds.\n\nURI: ${location.origin}\nVersion: 1\nChain ID: ${chainId}\nNonce: ${nonce}\nIssued At: ${issued.toISOString()}\nExpiration Time: ${expires.toISOString()}`;
      const signature=await window.ethereum.request({method:'personal_sign',params:[message,address]});
      if(typeof signature!=='string'||!signature.startsWith('0x'))throw new Error('The wallet did not return a signature.');
      const valid=await verifyMessage({address,message,signature:signature as `0x${string}`});
      if(!valid)throw new Error('The signature did not match this wallet.');
      setSignedIn(true);
    }catch(e){setError(e instanceof Error?e.message:'Signature request was cancelled.');setSignedIn(false);}
    finally{setBusy(false);}
  };

  const switchToRobinhood=async()=>{
    if(!window.ethereum)return;
    setBusy(true);setError('');
    try{
      try { await window.ethereum.request({method:'wallet_switchEthereumChain',params:[{chainId:'0x1237'}]}); }
      catch(e){
        if((e as {code?:number}).code!==4902)throw e;
        await window.ethereum.request({method:'wallet_addEthereumChain',params:[{chainId:'0x1237',chainName:'Robinhood Chain',nativeCurrency:{name:'Ether',symbol:'ETH',decimals:18},rpcUrls:['https://rpc.mainnet.chain.robinhood.com/'],blockExplorerUrls:['https://robinhoodchain.blockscout.com/']}]});
      }
      setChainId(4663);setSignedIn(false);
    }catch(e){setError(e instanceof Error?e.message:'Network switch was cancelled.');}
    finally{setBusy(false);}
  };
  const disconnect=()=>{setAddress(null);setChainId(null);setSignedIn(false);setError('');};
  return {available,address,chainId,signedIn,busy,error,connect,signIn,switchToRobinhood,disconnect};
}

export type WalletState = ReturnType<typeof useWallet>;
