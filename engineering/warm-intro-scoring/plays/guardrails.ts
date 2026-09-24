/** Strict cloud boundaries; reference compatibility is not source verification. */
export function requireEvidenceRegistry(data:any):void {
 if(!data||!Array.isArray(data.evidence))throw new Error('An explicit evidence registry is required, including [] for zero evidence');
}

export function expandFeatureCatalog(data:any):void {
 if(data.feature_catalog===undefined)return;
 if(!Array.isArray(data.feature_catalog)||!Array.isArray(data.paths))throw Error('Invalid feature catalog');
 for(const path of data.paths)for(const key of Object.keys(path.features||{})){
  const index=path.features[key];
  if(!Number.isInteger(index)||index<0||index>=data.feature_catalog.length||!data.feature_catalog[index])throw Error('Invalid feature catalog index');
  path.features[key]=data.feature_catalog[index];
 }
}
