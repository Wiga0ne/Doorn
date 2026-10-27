// Bruit de fond : souffle / ronflement en entree, sortie avec et sans noise gate.
// g++ -O2 -std=c++17 -I. tests/test_noise.cpp -o /tmp/test_noise && /tmp/test_noise
#include "DoornDSP.h"
#include <cstdio>
#include <random>
using namespace doorn;
static double rmsdb(const std::vector<float>& x,size_t a){double s=0;for(size_t i=a;i<x.size();++i)s+=x[i]*x[i];return 10*std::log10(s/(x.size()-a)+1e-30);}
int main(){
  const double sr=48000; std::mt19937 rng(3); std::normal_distribution<float> n(0,1);
  struct In{const char*nm; double db; bool hum;};
  In ins[]={{"silence",-400,false},{"hiss-90",-90,false},{"hiss-80",-80,false},{"hiss-70",-70,false},{"hum50-70",-70,true}};
  struct C{const char*nm; Params p;};
  Params b; std::vector<C> cs;
  {Params p=b;p.gate=0;cs.push_back({"def_nogate",p});}
  cs.push_back({"default",b});
  {Params p=b;p.gate=1;cs.push_back({"g_low",p});}
  {Params p=b;p.gate=3;cs.push_back({"g_high",p});}
  {Params p=b;p.treble=5;p.bass=5;p.mids=5;cs.push_back({"eqflat",p});}
  {Params p=b;p.boostOn=true;cs.push_back({"boost",p});}
  {Params p=b;p.gain=10;p.boost=10;p.boostOn=true;cs.push_back({"max",p});}
  {Params p=b;p.active=false;cs.push_back({"bypass",p});}
  printf("%-10s","");for(auto&i:ins)printf("%10s",i.nm);printf("\n");
  for(auto&c:cs){printf("%-10s",c.nm);
   for(auto&i:ins){Engine e;e.prepare(sr,1);std::vector<float> x((size_t)(sr*3));
    double a=std::pow(10,i.db/20);
    for(size_t k=0;k<x.size();++k) x[k]= i.hum? (float)(a*1.41*std::sin(2*M_PI*50*k/sr)+0.3*a*1.41*std::sin(2*M_PI*150*k/sr)) : (float)(a*n(rng));
    for(size_t k=0;k<x.size();k+=256){float*p[1]={x.data()+k};e.process(p,(int)std::min<size_t>(256,x.size()-k),c.p);}
    printf("%10.1f",rmsdb(x,(size_t)sr));}
   printf("\n");}
}
