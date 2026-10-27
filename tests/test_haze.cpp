// Sifflement / grésillement en tenue : corde raide (partiels etires) + souffle, analyse par tests/haze.py
// g++ -O2 -std=c++17 -I. tests/test_haze.cpp -o /tmp/h && /tmp/h 44100 8.5 6.5 5 6 2 0 1 -95 && python3 tests/haze.py
#include "../DoornDSP.h"
#include <cstdio>
#include <random>
using namespace doorn;
// corde parfaitement harmonique (52 Hz) : toute energie hors harmoniques vient du plugin
int main(int argc,char**argv){
  const double sr=argc>1?atof(argv[1]):44100; const double f0=52.0;
  std::vector<float> x((size_t)(sr*6),0.f); std::mt19937 r(1); std::normal_distribution<float> n(0,1);
  for(size_t i=0;i<x.size();++i){double t=i/sr; double s=0;
    for(int h=1;h<=90;++h){ if(h*f0>sr*0.45) break; s+= std::sin(2*M_PI*h*f0*std::sqrt(1+0.00012*h*h)*t + h*0.7)/ (h*1.0) * std::exp(-t*(0.4+0.05*h)); }
    x[i]=(float)(0.12*s);
  }
  double nz=argc>9?std::pow(10,atof(argv[9])/20):0; for(auto&v:x) v+=(float)(nz*n(r));
  for(int i=0;i<(int)(0.004*sr);++i) x[i]+=0.05f*n(r)*(1-i/(0.004*sr));
  Params p; if(argc>2){ p.gain=atof(argv[2]); p.treble=atof(argv[3]); p.mids=atof(argv[4]); p.bass=atof(argv[5]); p.mode=atoi(argv[6]); p.boostOn=atoi(argv[7]); p.eq=atoi(argv[8]); p.boost=7.5; p.level=7;}

  Engine e; e.prepare(sr,1);
  for(size_t k=0;k<x.size();k+=256){float*pp[1]={x.data()+k}; e.process(pp,(int)std::min<size_t>(256,x.size()-k),p);}
  FILE*f=fopen("out.raw","wb"); fwrite(x.data(),4,x.size(),f); fclose(f);
}
