// Preserve session positions and restart paths after unavailable values.
export function segments<T>(points: T[], valid: (p:T)=>boolean): Array<Array<{point:T; index:number}>> {
  const result:Array<Array<{point:T;index:number}>>=[];
  let current:Array<{point:T;index:number}>=[];
  points.forEach((point,index)=>{
    if(valid(point)) current.push({point,index});
    else if(current.length){result.push(current);current=[];}
  });
  if(current.length) result.push(current);
  return result;
}
export function linePath<T>(points:T[], value:(p:T)=>number|null|undefined, x:(index:number)=>number, y:(v:number)=>number) {
  return segments(points,p=>typeof value(p)==="number"&&Number.isFinite(value(p)))
    .map(group=>group.map(({point,index},i)=>`${i?"L":"M"} ${x(index)} ${y(value(point) as number)}`).join(" ")).join(" ");
}
