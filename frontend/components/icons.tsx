export function Icon({name,size=18}:{name:string;size?:number}){
 const paths:Record<string,React.ReactNode>={
 orders:<><rect x="4" y="4" width="16" height="17" rx="3"/><path d="M8 3v4m8-4v4M8 12h8m-8 4h5"/></>,
 assistant:<><rect x="4" y="7" width="16" height="13" rx="4"/><path d="M12 3v4m-4 6h.01M16 13h.01M9 17h6"/></>,
 integrations:<><rect x="3" y="3" width="7" height="7" rx="2"/><rect x="14" y="3" width="7" height="7" rx="2"/><rect x="3" y="14" width="7" height="7" rx="2"/><rect x="14" y="14" width="7" height="7" rx="2"/></>,
 arrow:<path d="M5 12h14m-5-5 5 5-5 5"/>,back:<path d="M19 12H5m5-5-5 5 5 5"/>,plus:<path d="M12 5v14M5 12h14"/>,
 search:<><circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 4 4"/></>,clock:<><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></>,
 check:<path d="m5 12 4 4L19 6"/>,close:<path d="m6 6 12 12M6 18 18 6"/>,external:<><path d="M14 4h6v6m0-6L10 14"/><path d="M10 4H5a1 1 0 0 0-1 1v14a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-5"/></>,
 warning:<><path d="m12 3 10 18H2L12 3Z"/><path d="M12 9v5m0 3h.01"/></>,pause:<path d="M8 5v14M16 5v14"/>,play:<path d="m8 4 12 8-12 8V4Z"/>,
 message:<><path d="M21 11a8 8 0 0 1-8 8H5l-3 3V11a9 9 0 0 1 19 0Z"/><path d="M7 10h10m-10 4h6"/></>,
 };
 return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name]||paths.orders}</svg>;
}
