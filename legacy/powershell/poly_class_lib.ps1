<#	
	.NOTES
	===========================================================================
	 Created with: 	SAPIEN Technologies, Inc., PowerShell Studio 2016 v5.2.119
	 Created on:   	4/13/2016 9:21 PM
	 Created by:   	Cit
	 Organization: 	Fort
	 Filename:     	poly_class_lib.ps1
	===========================================================================
	.DESCRIPTION
		A description of the file.
#>



#region enumerator_storage

enum group_type
{
	house = 1
	relationship = 2
	other = 3
}

enum rel_type
{
	romantic = 1
	dominant = 2
	submissive = 3
	playmate = 4
	fluctuating = 5
	undefined = 6
}

enum power_dynamic_type
{
	undefined = 0
	pupplay = 1
	ageplay = 2
}

#endregion

#region class_storage

class group
{
	[int]$group_id
	[string]$group_name
	[bool]$group_active
	[group_type]$group_type
	[System.Array]$members
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

class member
{
	[int]$member_id
	[string]$member_name
	[bool]$member_active
	[System.Array]$relationships
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

class relationship
{
	[bool]$rel_active
	[string]$rel_type
	[string]$power_dynamic_type
	[System.Array]$members
	[string]$member_1_title
	[string]$member_2_title
}


#endregion


#region function_storage

function Initialize-relationship
{
	param
	(
		[Parameter(Mandatory = $true,
				   Position = 0)]
		[object]$member_1,
		[Parameter(Mandatory = $true,
				   Position = 1)]
		[object]$memeber_2,
		[Parameter(Mandatory = $false,
				   Position = 2)]
		[string]$rel_type,
		[Parameter(Mandatory = $false,
				   Position = 3)]
		[string]$power_dynamic_type,
		[Parameter(Mandatory = $false,
				   Position = 4)]
		[string]$member_1_title,
		[Parameter(Mandatory = $false,
				   Position = 5)]
		[string]$member_2_title
	)
	
	$relationship = New-Object relationship
	$relationship.rel_active = $true
	$relationship.members = $member_1, $memeber_2
	if ($rel_type) { $relationship.rel_type = $rel_type }
	else { $relationship.rel_type = 6 }
	if ($power_dynamic_type) { $relationship.power_dynamic_type = $power_dynamic_type }
	else { $relationship.power_dynamic_typee = 0 }
	if ($member_1_title) { $relationship.member_1_title = $member_1_title }
	else { $relationship.member_1_title = $null }
	if ($member_2_title) { $relationship.member_2_title = $member_2_title }
	else { $relationship.member_2_title = $null }
	return $relationship
}



#endregion


#Initialize-relationship -member_1 "cit" -memeber_2 "devan" -rel_type 1 -power_dynamic_type 0 -member_1_title "lil bro" -member_2_title "big sis"