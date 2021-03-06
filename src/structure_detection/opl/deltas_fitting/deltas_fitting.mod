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
  
 float bigM=...; 
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
 dvar float+ maxDistance;
 dvar float+ maxPointDistance[p in P];
 
 
 execute {
 	var i,j;
 	var maxDistance = Distance_dp[1][1]
 	
 	for (i=1; i<=nDeltas; ++i)
 		for (j=1; j<=nPoints; ++j)
 		{
 			if (Distance_dp[i][j] > maxDistance)
 				maxDistance = Distance_dp[i][j]; 		
 		}
 	bigM = maxDistance;
 	writeln("The maximum distance is: ", bigM);
 }
 
 /**********************
  * Objective function *
  **********************/

  // Is more important to have less deltas than the maximum distance
  // so extra deltas have extra penalization of *100. This number should
  // be set empirically
  //minimize
  //	maxDistance + sum(d in D) UsedDelta[d];

  minimize
    sum (p in P) maxPointDistance[p] + sum(d in D) UsedDelta[d];
 
  subject to {
  	
  	// All points must be covered by exactly one delta
  	forall (p in P) sum (d in D) Cover_dp[d,p] == 1;
  	
  	// The sumation of used delta never can exceed 1.
  	sum (d in D) maxl(0,Deltas[d] - (1-UsedDelta[d])) <= 1;
  	  
  	// Good relation for Cover_dp and UsedDelta
  	forall (d in D) {
  		sum (p in P) Cover_dp[d,p] <= UsedDelta[d]*nPoints;
  		UsedDelta[d] <= sum (p in P) Cover_dp[d,p];
    }  		
  	
  	// Good value for maxDistance (assuming we are minimizing it)
  	//forall (d in D, p in P)
    //    maxl(Distance_dp[d,p] - (1-Cover_dp[d,p])*bigM, 0) <= maxDistance;

    forall (p in P, d in D)
        maxl(Distance_dp[d,p] - (1-Cover_dp[d,p])*bigM, 0) <= maxPointDistance[p];

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
  	
  	writeln("----------");
  	for (i=1; i<=nDeltas; ++i)
  	{
  		if (UsedDelta[i] == 1)
  		{
  			var pointsCovered = 0;
  			var j;
  			for (j=1; j <= nPoints; j++)
  				pointsCovered += Cover_dp[i][j];
  			
  			writeln("- Used delta[",i,"] = ", Deltas[i], ". Covers ", 
                pointsCovered, " points");
  				
  			total_delta += Deltas[i];
  			nUsedDeltas+=1;
  		}
  	}
  	writeln("----------");
  	writeln("Number of used deltas: ", nUsedDeltas);
  	writeln("Max distance: ", maxDistance);
  	writeln((total_delta*100), "% of the application is described.");
  }
