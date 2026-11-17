<#	
	.NOTES
	===========================================================================
	 Created with: 	SAPIEN Technologies, Inc., PowerShell Studio 2016 v5.2.119
	 Created on:   	4/13/2016 9:21 PM
	 Created by:   	Cit
	 Organization: 	Fort
	 Filename:     	
	===========================================================================
	.DESCRIPTION
		A description of the file.
#>



#region enumerator_storage

enum environments
{
	dev = 1
	intg = 2
	uat = 3
	load = 4
	fnst = 5
	fstrk = 6
	prod = 7
	dr = 8
}

enum status
{
	new = 1
	failed = 2
	successful = 3
	ready = 4
	pending = 5
	progress = 6
	waiting = 7
	completed = 8
	cancelled = 9
}

enum method
{
	get = 0
	post = 1
	put = 2
	blank = 3
	delete = 4
}

#endregion

#region function_storage
#endregion

#region class_storage

class data_api
{
	[int]$id
	[psobject]$output
	[bool]$success
	[string]$private:base_url = $config.api_url
	[method]$method
	get_data($url_target)
	{
		$url = $this.base_url + $url_target;
		try
		{
			$results = Invoke-RestMethod -Method Get -Uri $url -UseDefaultCredentials
			$this.Success = $true
			$this.output = $results
		}
		catch
		{
			$exception = $_.Exception.Message.ToString()
			$this.Success = $false
			$this.output = $exception
		}
	}
	change_data($url_target, $method, $body)
	{
		try
		{
			$json = $body | ConvertTo-Json
			$url = $this.base_url + $url_target;
			$results = Invoke-RestMethod -Method $method -Uri $url -Body $json -UseDefaultCredentials -ContentType application/json
			$this.Success = $true
			$this.output = $results
		}
		catch
		{
			$exception = $_.Exception.Message.ToString()
			$this.Success = $false
			$this.output = $exception
		}
	}
}


#endregion
