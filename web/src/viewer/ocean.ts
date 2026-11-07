import * as T from "three";

/** Presentation-only wave/lighting shader. Never used as boat telemetry or physics. */
export function oceanMaterial() {
  return new T.ShaderMaterial({
    uniforms: {
      uTime: { value: 0 },
      uSun: { value: new T.Vector3(-0.4, 0.4, -0.6).normalize() },
      uDusk: { value: 0 },
    },
    vertexShader: `
      #include <common>
      #include <logdepthbuf_pars_vertex>
      varying vec3 vWorld;
      void main() { vec4 p = modelMatrix * vec4(position,1.0); vWorld=p.xyz; gl_Position=projectionMatrix*viewMatrix*p;
        #include <logdepthbuf_vertex>
      }
    `,
    fragmentShader: `
      #include <logdepthbuf_pars_fragment>
      uniform float uTime; uniform vec3 uSun; uniform float uDusk;
      varying vec3 vWorld;
      vec3 normalAt(vec2 p) {
        float t=uTime;
        vec2 d=vec2(0.0);
        float pixel=max(length(dFdx(p)),length(dFdy(p)));
        float fine=1.-smoothstep(.2,1.5,pixel);
        float coarse=1.-smoothstep(.3,2.,pixel*.2);
        d+=vec2(.85,.52)*cos(dot(p,vec2(.85,.52))*.13+t*.75)*.11*coarse;
        d+=vec2(-.35,.94)*cos(dot(p,vec2(-.35,.94))*.25-t*1.1)*.07*coarse;
        d+=vec2(.94,-.34)*cos(dot(p,vec2(.94,-.34))*.83+t*1.65)*.045*fine;
        d+=vec2(.25,.97)*cos(dot(p,vec2(.25,.97))*2.45-t*2.1)*.022*fine*fine;
        d+=vec2(.71,.71)*cos(dot(p,vec2(.71,.71))*5.8+t*3.1)*.009*fine*fine;
        return normalize(vec3(-d.x,1.,-d.y));
      }
      void main(){
        vec3 n=normalAt(vWorld.xz), eye=normalize(cameraPosition-vWorld);
        float fresnel=.025+.975*pow(1.-max(dot(n,eye),0.),5.);
        vec3 reflected=reflect(-eye,n);
        vec3 sky=mix(vec3(.66,.78,.83),vec3(.2,.43,.62),pow(max(reflected.y,0.),.45));
        sky=mix(sky,vec3(.39,.35,.36)+vec3(.3,.12,.025)*pow(max(dot(reflected,uSun),0.),8.),uDusk*.7);
        vec3 deep=mix(vec3(.015,.115,.14),vec3(.035,.09,.12),uDusk);
        vec3 colour=mix(deep,sky,fresnel*.86);
        float sun=pow(max(dot(reflect(-uSun,n),eye),0.),180.);
        float glitter=pow(max(dot(reflect(-uSun,n),eye),0.),24.)*.08;
        colour+=(vec3(1.,.91,.7)-vec3(0.,.2,.32)*uDusk)*(sun*1.1+glitter);
        float distanceToEye=length(cameraPosition-vWorld);
        float haze=1.-exp(-distanceToEye*.0000035);
        colour=mix(colour,mix(vec3(.62,.75,.8),vec3(.46,.42,.43),uDusk),haze);
        #include <logdepthbuf_fragment>
        gl_FragColor=vec4(colour,1.);
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
      }
    `,
  });
}
