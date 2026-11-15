import {Icon} from './icons';
import {pretty} from '../lib/types';
export function Badge({value}:{value:string}){return <span className={'badge badge-'+value}><span/>{pretty(value)}</span>}
export function PageHeading({eyebrow,title,description,action}:{eyebrow?:string;title:string;description:string;action?:React.ReactNode}){return <div className="page-heading"><div>{eyebrow&&<p className="eyebrow">{eyebrow}</p>}<h1>{title}</h1><p>{description}</p></div>{action&&<div className="heading-action">{action}</div>}</div>}
export function Empty({title,children}:{title:string;children?:React.ReactNode}){return <div className="empty-state"><span className="empty-icon"><Icon name="orders" size={27}/></span><h3>{title}</h3><div>{children}</div></div>}
