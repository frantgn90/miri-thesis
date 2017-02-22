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
 int nDeltas=...;
 
 range D=1..nDeltas;
 range P=1..nPoints;
 range Dim=1..2;
 
 float Points[p in P, dim in Dim]=...;
 float Distance_dp[d in D, p in P]=...;
 float Deltas[d in D]=...;
 
 /**********************
  * Decision variables *
  **********************/
 
 // Wheter this delta is used or not
 dvar boolean UsedDelta[d in D];
 
 // Whether delta d covers the point p or not
 dvar boolean Cover_dp[d in D][p in P];
 
 // The maximum distance from function delta to points that are
 // covered by it
 dvar float maxDeltaDistance[d in D];
 
 // Number of used delta functions
 dvar int nUsedDeltas;
 
 // Maximum of the delta mean distances with points
 dvar float maxDistance;
 
 
 /**************
   * Preprocess *
   **************/
   
 /*execute {
  	var next_delta=accuracy;
  	var i, j;
  	
  	writeln("Number of deltas: ", nDeltas);
  	
  	// Deltas initialization
  	for (i=1; i<=nDeltas; ++i)
  	{
  	  	writeln("- Delta[", i ,"] = ", next_delta);
  		Deltas[i]=next_delta;
  		next_delta+=accuracy;
  	}
  	
  	// Distances calculation
  	for (i=1; i<=nDeltas; ++i)
  		for (j=1; j<=nPoints; ++j)
  		{
  			Distance_dp[i][j] = Math.abs(Points[j][1]-((TotalTime*Deltas[i])/Points[j][2]));
   		}  			
  }*/
 
 /**********************
  * Objective function *
  **********************/

  
  minimize
  	maxDistance;
  	//maxDistance - sum (d in D, p in P) Cover_dp[d,p];
  	//sum(d in D) maxDeltaDistance[d]; 
  	//nUsedDeltas + maxDistance;
 
  subject to {
    
  	// The sumation of used delta never can exceed 1.
  	sum (d in D) maxl(Deltas[d] - bigM*(1-UsedDelta[d]), 0) <= 1;
  	
  	// Good value for nUsedDeltas
  	sum(d in D) UsedDelta[d] <= nUsedDeltas;
  	
  	// If the delta is used it must cover at least one point.
  	// No point otherwise
  	forall (d in D)
  	  sum (p in P) Cover_dp[d,p] <= UsedDelta[d]*nPoints;
  		
  	// All points must be covered by exactly one delta
  	forall (p in P)
  	  sum (d in D) Cover_dp[d,p] == 1;
  	
  	// Good value for maxDeltaDistance
  	forall (d in D, p in P)
  	  maxl(0,(Distance_dp[d,p] - (1-Cover_dp[d,p])*bigM)) <= maxDeltaDistance[d];
  	
  	// Good value for maxDistance
  	forall (d in D)
  	  maxl(0,maxDeltaDistance[d] - (1-UsedDelta[d])*bigM) <= maxDistance;
  	  
  }
  
  /***************
   * Postprocess *
   ***************/
   
  execute {
  	// At this preprocess all of deltas must be generated 
  	var i;
  	
  	writeln("Maximum distance: ", maxDistance);
  	writeln("Number of used deltas: ", nUsedDeltas, "\n");
  	
  	var total_delta = 0;
  	for (i=1; i<=nDeltas; ++i)
  	{
  		if (UsedDelta[i] == 1)
  		{
  			writeln("- Used delta[",i,"] = ", Deltas[i], " , Max distance = ", 
  				maxDeltaDistance[i]);
  			total_delta += Deltas[i];
  		}
  	}
  	writeln("\n");
  	writeln((total_delta*100), "% of the application is described.");
  }