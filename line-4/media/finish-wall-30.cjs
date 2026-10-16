// Transfer only generated pigment into bare rock; preserve every other RGB pixel.
// Reads workspace image inputs only. No network or configuration access.
const fs=require('node:fs'), zlib=require('node:zlib'), crypto=require('node:crypto');
const {decode,encode,thumbnail}=require('../../line-1/media/finish-wall.cjs');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
function generated(bytes) {
 if(bytes.subarray(0,8).toString('hex')!=='89504e470d0a1a0a') throw Error('PNG required');
 let width,height,channels,parts=[];
 for(let off=8;off<bytes.length;) {
  const size=bytes.readUInt32BE(off),type=bytes.toString('ascii',off+4,off+8),data=bytes.subarray(off+8,off+8+size);
  if(type==='IHDR') {
   width=data.readUInt32BE(0);height=data.readUInt32BE(4);channels=data[9]===2?3:data[9]===6?4:0;
   if(!channels||data[8]!==8||data[12]!==0||width!==1024||height!==1024) throw Error('unexpected generated format');
  }
  if(type==='IDAT') parts.push(data);
  off+=size+12;if(type==='IEND')break;
 }
 const stride=width*channels,raw=zlib.inflateSync(Buffer.concat(parts),{maxOutputLength:(stride+1)*height});
 const pixels=Buffer.alloc(stride*height);
 if(raw.length!==(stride+1)*height)throw Error('raster length');
 for(let y=0;y<height;y++)for(let x=0;x<stride;x++) {
  const i=y*stride+x,a=x>=channels?pixels[i-channels]:0,b=y?pixels[i-stride]:0,c=y&&x>=channels?pixels[i-stride-channels]:0;
  const p=a+b-c,pa=Math.abs(p-a),pb=Math.abs(p-b),pc=Math.abs(p-c),filter=raw[y*(stride+1)];
  if(filter>4)throw Error('filter');
  const predictor=[0,a,b,Math.floor((a+b)/2),pa<=pb&&pa<=pc?a:pb<=pc?b:c][filter];
  pixels[i]=(raw[y*(stride+1)+x+1]+predictor)&255;
 }
 return {width,height,channels,pixels};
}
const base=fs.readFileSync('artifacts/line-4/wall-v10.png');
if(JSON.parse(fs.readFileSync('dist/line-4/29.json')).image!=='https://api.imd.fun/artifacts/'+sha(base))throw Error('ancestor mismatch');
const raw=fs.readFileSync('artifacts/line-4/wall-v11.png'),old=decode(base),gen=generated(raw);
const out={...old,pixels:Buffer.from(old.pixels)},bounds=[845,941,1024,1045];
let changed=0;
for(let y=bounds[1];y<=bounds[3];y++)for(let x=bounds[0];x<=bounds[2];x++) {
 // Area-sample the generated pigment, discarding its entire generated rock backdrop.
 let black=0,ochre=0,n=0;
 const sx0=210+(x-bounds[0])*620/180,sy0=300+(y-bounds[1])*390/105;
 for(let sy=Math.floor(sy0);sy<Math.ceil(sy0+390/105);sy++)for(let sx=Math.floor(sx0);sx<Math.ceil(sx0+620/180);sx++) {
  const at=(sy*gen.width+sx)*gen.channels,r=gen.pixels[at],g=gen.pixels[at+1],b=gen.pixels[at+2];
  n++;if(Math.max(r,g,b)<85)black++;else if(r>170&&g>150&&b<110&&g/r>.79)ochre++;
 }
 const at=(y*old.width+x)*3,grain=.72+.28*((old.pixels[at]+old.pixels[at+1])/510);
 const ab=.63*black/n*grain,ao=.65*ochre/n*grain,alpha=ab+ao;
 if(alpha===0)continue;
 for(let c=0;c<3;c++)out.pixels[at+c]=Math.round(old.pixels[at+c]*(1-alpha)+[36,27,18][c]*ab+[175,113,35][c]*ao);
 if(!out.pixels.subarray(at,at+3).equals(old.pixels.subarray(at,at+3)))changed++;
}
let outside=0;
for(let y=0;y<old.height;y++)for(let x=0;x<old.width;x++) {
 if(x>=bounds[0]&&x<=bounds[2]&&y>=bounds[1]&&y<=bounds[3])continue;
 const at=(y*old.width+x)*3;
 if(!old.pixels.subarray(at,at+3).equals(out.pixels.subarray(at,at+3)))outside++;
}
if(changed<1000||outside)throw Error('preservation failed');
const png=encode(out),jpg=thumbnail(out);
if(!decode(png).pixels.equals(out.pixels)||jpg.length>100000)throw Error('media check failed');
fs.writeFileSync('artifacts/line-4/wall-v11.png',png);
fs.unlinkSync('artifacts/line-4/wall.png');fs.linkSync('artifacts/line-4/wall-v11.png','artifacts/line-4/wall.png');
fs.writeFileSync('artifacts/line-4/30.jpg',jpg);fs.linkSync('artifacts/line-4/30.jpg','dist/line-4/30.jpg');
const report={source:'artifacts/line-4/wall-v10.png',source_sha256:sha(base),generated_sha256:sha(raw),
 wall:'artifacts/line-4/wall-v11.png',sha256:sha(png),width:out.width,height:out.height,format:'PNG',mode:'RGB',bytes:png.length,
 preview:'dist/line-4/30.jpg',preview_width:512,preview_height:512,preview_format:'JPEG',preview_bytes:jpg.length,
 preview_sha256:sha(jpg),addition_bounds_inclusive:bounds,changed_pixels:changed,changed_pixels_outside_addition:outside,png_roundtrip_passed:true};
fs.writeFileSync('line-4/media-check-30.json',JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify(report,null,2));
