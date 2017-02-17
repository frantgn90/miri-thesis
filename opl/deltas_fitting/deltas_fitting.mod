/*********************************************
 * OPL 12.6.0.0 Model
 * Author: jmartinez
 * Creation Date: 17/02/2017 at 09:38:55
 *********************************************/
 
 /**************
  * Input data *
  **************/
  
 int bigM=...; 
 int nPoints=...;
 int accuracy=...;
 int nDeltas=...;
 
 range D=1..nDeltas;
 range P=1..nPoints;
 
 int Points[p in P]=...;
 float Deltas[d in D];
 
 /**********************
  * Decision variables *
  **********************/
 
 // Wheter this delta is used or not
 dvar boolean used_d[d in D];
 
 // Whether delta d covers the point p or not
 dvar boolean covers_dp[d in D][p in P];
 
 // The mean distance from function delta to points that are
 // covered by it
 dvar float dist_mean[d in D];
 
 // Number of used delta functions
 dvar int nUsedDeltas;
 
 
 /**************
   * Preprocess *
   **************/
  execute {
  	// At this preprocess all of deltas must be generated 
  	int next_delta;
  	
  	forall (d in D){
  		Deltas[d]=accuracy;
  		accuracy+=accuracy;  	
  	}
  }
 
 /**********************
  * Objective function *
  **********************/
  
  minimize nUsedDeltas*bigM + sum(p in P) dist_mean[p];
 
  subject to {
    
  	// The sumation of used delta never can exceed 1. This is because
  	// every delta is the portion of time that a loop is explaining over
  	// the total application time. Then at most all loops will explain
  	// the whole application.
  	
  	
  	// All points must be covered for one and only one of the deltas
  	
  	  
  	// Good value for mean distance
  	
  }