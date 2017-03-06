/**********************************************************************
 * OPL 12.6.0.0 Model                                                 *
 * Author: jmartinez                                                  *
 * Creation Date: 17/02/2017 at 09:38:55                              *
 *                                                                    *
 * As inputs there are multiple points in a 2D space. Those           *
 * points are scattered following certain patterns. Has been          *
 * detected that those patters are in fact functions that follows     *
 * the expression T/N being (does not matter the meaning).            *
 * The difficult part is that the points are not following just one   *
 * T/N function but many similar ones, defined by (delta*T)/N         *
 * where 0 < delta < 1.                                               *
 *                                                                    *
 * The objective of this model is to end up with all the function     *
 * (different delta) that can cover all points with the               *
 * main restriction that the sumation of all deltas must be <= 1,     *
 * following the minimum squares theorem.							  *
 **********************************************************************/
 
 
 
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
 dvar float+ maxDeltaDistance[d in D];
 
 
 /**********************
  * Objective function *
  **********************/

  minimize
  	//sum(d in D) UsedDelta[d] + maxDistance;
  	//sum(d in D) UsedDelta[d];
  	sum(d in D) maxDeltaDistance[d] - sum(d in D) UsedDelta[d]*bigM;
 
  subject to {
  	
  	// All points must be covered by exactly one delta
  	forall (p in P) sum (d in D) Cover_dp[d,p] == 1;
  	
  	// The sumation of used delta never can exceed 1.
  	sum (d in D) maxl(Deltas[d] - bigM*(1-UsedDelta[d]), 0) <= 1;
  	  
  	// Good relation for Cover_dp and UsedDelta
  	forall (d in D) {
  		sum (p in P) Cover_dp[d,p] <= UsedDelta[d]*nPoints;
  		UsedDelta[d] <= sum (p in P) Cover_dp[d,p];
    }  		
  	
  	// Good value for maxDeltaDistance
  	forall (d in D, p in P)
  	  	Distance_dp[d,p] - (1-Cover_dp[d,p])*bigM <= maxDeltaDistance[d];
  	  
  }
  
  /***************
   * Postprocess *
   ***************/
   
  execute {
  	// At this preprocess all of deltas must be generated 
  	var i;
  	
  	//writeln("Maximum distance: ", maxDistance);
  	var nUsedDeltas = 0;
  	var total_delta = 0;
  	
  	for (i=1; i<=nDeltas; ++i)
  	{
  		if (UsedDelta[i] == 1)
  		{
  			writeln("- Used delta[",i,"] = ", Deltas[i], " , Max distance = ", 
  				maxDeltaDistance[i]);
  			total_delta += Deltas[i];
  			nUsedDeltas+=1;
  		}
  	}
  	writeln("\n");
  	writeln("Number of used deltas: ", nUsedDeltas);
  	writeln((total_delta*100), "% of the application is described.");
  }